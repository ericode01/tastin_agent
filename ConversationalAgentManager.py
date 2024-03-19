import json
import re
from typing import Optional

from haystack.agents.base import Tool
from haystack.agents.memory import ConversationSummaryMemory
from haystack.agents.conversational import ConversationalAgent
from haystack import Pipeline
from haystack.document_stores import PineconeDocumentStore
from haystack.nodes import AnswerParser, EmbeddingRetriever, PromptNode, PromptTemplate

from components.document_merger_with_business_id import DocumentMergerWithBusinessId
from components.embedding_retriever_input_helper import EmbeddingRetrieverInputHelper
from components.geographic_coordinates_retriever import GeographicCoordinatesRetriever


class ConversationalAgentManager:
    def __init__(self):
        self.session_agent_map = {}
        self.response_text_pattern = r"(?s)(.*){['\"]references['\"]:.*}"
        self.references_json_pattern = r"\{['\"]references['\"]:.*\}"

    def ask_agent(self, user_prompt: str, session_id: str):
        if session_id not in self.session_agent_map:
            conversational_agent = self.initialize_new_conversational_agent_2()
            self.session_agent_map[session_id] = conversational_agent
        else:
            conversational_agent = self.session_agent_map[session_id]

        result = conversational_agent.run(user_prompt)

        references_json_str = self.extract_text_based_on_regex(
            original_text=result['answers'][0].answer,
            regex=self.references_json_pattern,
            extract_group_num=0
        )

        if references_json_str:
            response_text = self.extract_text_based_on_regex(
                original_text=result['answers'][0].answer,
                regex=self.response_text_pattern,
                extract_group_num=1
            )
        else:
            response_text = result['answers'][0].answer

        references_json = self.deserialize_json(references_json_str)

        if "references" not in references_json or "business_id" not in references_json["references"]:
            references_json = {}

        print("conversational_agent.run: " + json.dumps(result['answers'][0].answer))

        return {
            "response_text": response_text,
            "references_json": references_json
        }

    def deserialize_json(self, s: str):
        if not s:
            return {}

        try:
            s = s.lower()
            s = s.replace("'", "\"")
            json_data = json.loads(s)
            return json_data
        except Exception as ex:
            print("string is not json deserializable. ", ex, s)
            return {}

    def extract_text_based_on_regex(self, original_text: str, regex: str, extract_group_num: int) -> Optional[str]:
        # Search for a match with the final answer pattern in the prompt node response
        match = re.search(regex, original_text)

        if match:
            # If a match is found, get the certain group (i.e., the content inside the parentheses of the regex pattern)
            result = match.group(extract_group_num)

            # Remove leading/trailing quotes and whitespaces, then return the final answer
            return result.strip('" \n')  # type: ignore
        else:
            # If no match is found, return None
            return None

    def initialize_new_conversational_agent_2(self):

        # restaurant_finder_tool
        document_store = PineconeDocumentStore(api_key='eb580754-c4c7-473d-9fcb-aa1d37c94a5c',
                                               similarity="cosine",
                                               embedding_dim=4096,
                                               environment="gcp-starter",
                                               index="business1"
                                               )

        embedding_retriever_input_helper = EmbeddingRetrieverInputHelper()

        retriever = EmbeddingRetriever(document_store=document_store,
                                       embedding_model="embed-english-v2.0",
                                       api_key="lfT5FlajkN9dFGO04V5hHcUkTPeNHmaA4uE1xwLw",
                                       model_format="cohere",
                                       top_k=3)

        document_merger = DocumentMergerWithBusinessId(separator="\n")

        restaurant_finder_pipeline = Pipeline()
        restaurant_finder_pipeline.add_node(component=embedding_retriever_input_helper, name="EmbeddingRetrieverInputHelper", inputs=["Query"])
        restaurant_finder_pipeline.add_node(component=retriever, name="Retriever", inputs=["EmbeddingRetrieverInputHelper.output_1"])
        restaurant_finder_pipeline.add_node(component=document_merger, name="DocumentMerger", inputs=["Retriever"])

        restaurant_finder_tool = Tool(name="Restaurant_Finder",
                                      description="Useful when you need to find restaurants and their descriptions based on a query around a location(specified by a latitude and a longitude). If the latitude and longitude of the location is unknown, need to use other tool to find out the location latitude and longitude first. Input is a JSON in this format {\"Query\":\"[The query based on which to find the restaurants.]\", \"Latitude\":[The latitude of the location to find the restaurants], \"Longitude\":[The longitude of the location to find the restaurants]}",
                                      pipeline_or_node=restaurant_finder_pipeline,
                                      output_variable="documents"
                                      )


        # geographic_coordinates_retriever_tool
        geographic_coordinates_retriever = GeographicCoordinatesRetriever()
        geographic_coordinates_retriever_pipeline = Pipeline()
        geographic_coordinates_retriever_pipeline.add_node(component=geographic_coordinates_retriever,
                                                           name="GeographicCoordinatesRetriever", inputs=["Query"])
        geographic_coordinates_retriever_tool = Tool(name="Geographic_Coordinates_Retriever",
                                                     description="Useful when you need to get the latitude and longitude of a location. Input is the location string.",
                                                     pipeline_or_node=geographic_coordinates_retriever_pipeline,
                                                     output_variable="coordinates_str"
                                                     )


        # summary_memory
        model_name = "gpt-4"
        prompt_node = PromptNode(model_name, api_key="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",
                                 max_length=1000)

        summary_memory = ConversationSummaryMemory(prompt_node, prompt_template="deepset/conversational-summary")

        conversational_agent_prompt = """
As Tastin, an intelligent personalized dining assistant, you assist users with inquiries related to dining out. Your responses are always well-informed, engaging, detailed and friendly. NEVER mention Google, Google reviews, or specific ratings and counts. NEVER ask a user to contact a restaurant.

For each query, you should start your response in only one of these ways:

1. "Final Answer:" - Use this to begin a direct, detailed response if you're certain about the answer.
2. If unsure or needing updated information, use your tools to gather current data. Indicate this process with:
   - "Thought:" followed by a brief explanation of your reasoning.
   - "Tool:" {tool_names} and on a new line, "Tool Input:" with the specific input for the tool and should be presented separately on a new line.

The "Final Answer" is a comprehensive and informative answer with just enough details to the human user's question in a natual and friendly way. If the query from the user is vague, in the "Final Answer", you can seek additional details from the user if asking a question can help you serve the user better.
When giving "Final Answer", include referenced content IDs in JSON format at the end on a new line, deciding based on the conversation's flow whether to show these references to the user. Always set show_references to true if you use this reference the first time. Format: {{"references": {{[id_key_name(don't add s)]:[list of comma-seperated IDs]}},"show_references":true if based on the user's previous interactions you think the user is better to see the references; false if based on the user's previous interactions you think the user has already seen the references recently and doesn't to show the references again}}
When using tools, your observation of the tool's result is trusted and marked as "Observation:". 
When looking for restaurants, always use tools.
When some information is missing, always try to use tools to gather information.
Answer in the same language as the user's message.
Your message can potentially contain emoji to make it more lively and friendly.
If you would give an answer covering broader scope (such as broader cuisine, broader category) than what was exactly asked by the user, give a reasonable explanation.

You have access to these tools:
{tool_names_with_descriptions}

Below is the previous conversation between the user and you:
{memory}

Your response to a query should be structured as follows:
- Thought: [Your initial reasoning]
- Followed by either a direct answer i.e. "Final Answer" or tool usage details.

Question: {query}
Thought:
{transcript}
        """

        conversational_agent = ConversationalAgent(prompt_node=prompt_node, memory=summary_memory,
                                                   tools=[geographic_coordinates_retriever_tool, restaurant_finder_tool],
                                                   prompt_template=conversational_agent_prompt)
        conversational_agent.final_answer_pattern = r"(?s)Final Answer\s*:\s*(.*)"

        return conversational_agent

    def initialize_new_conversational_agent(self):
        document_store = PineconeDocumentStore(api_key='eb580754-c4c7-473d-9fcb-aa1d37c94a5c',
                                               similarity="cosine",
                                               embedding_dim=4096,
                                               environment="gcp-starter",
                                               index="business1"
                                               )

        retriever = EmbeddingRetriever(document_store=document_store,
                                       embedding_model="embed-english-v2.0",
                                       api_key="lfT5FlajkN9dFGO04V5hHcUkTPeNHmaA4uE1xwLw",
                                       model_format="cohere",
                                       top_k=3)

        document_merger = DocumentMergerWithBusinessId(separator="\n")

        query_pipeline = Pipeline()
        query_pipeline.add_node(component=retriever, name="Retriever", inputs=["Query"])
        query_pipeline.add_node(component=document_merger, name="DocumentMerger", inputs=["Retriever"])

        restaurant_description_tool = Tool(name="Food_And_Restaurant_Consultant",
                                           description="Useful when you need to retrieve information on restaurants, dining out and anything about food.",
                                           pipeline_or_node=query_pipeline,
                                           output_variable="documents"
                                           )

        model_name = "gpt-4"
        prompt_node = PromptNode(model_name, api_key="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",
                                 max_length=1000)

        summary_memory = ConversationSummaryMemory(prompt_node, prompt_template="deepset/conversational-summary")

        conversational_agent_prompt_old = """
        In the following conversation, a human user interacts with you. You are an intelligent advisor called Weat helping a user with questions about restaurant, dining out, cooking at home and anything about food.
        The human user poses questions, and you go through several steps to provide well-informed answers in a natual, friendly, comprehensive and informative way.
        Do not mention Google or Google review. Do not mention any actual rating number and count in the answer. Do not include ID in the answer.
        If you know the answer, the response begins with "Final Answer:" on a new line.
        If you are uncertain or concerned that the information may be outdated or inaccurate, you must use the available tools to find the most up-to-date information. You have access to these tools:
        {tool_names_with_descriptions}

        The following is the previous conversation between a human and you:
        {memory}

        Your responses must start with one of the following:

        Thought: [Your reasoning process in short]
        Tool: {tool_names} (on a new line) Tool Input: [input for the selected tool WITHOUT quotation marks and on a new line] (These must always be provided together and on separate lines.)
        Final Answer: final comprehensive and informative answer with as much details as possible to the human user's question in a natual and friendly way. Also include all referenced content ID you used in the answer at the bottom of the Final Answer on a new line in the JSON format: {{'References': {{[id_key_name]:[list of comma-seperated IDs]}},'show_references':True if based on the previous conversataion you think the user is better to see the references; False if based on the previous conversation you think the user has already seen the references recently and doesn't to show the references again}}.
        When selecting a tool, you must provide both the "Tool:" and "Tool Input:" pair in the same response, but on separate lines. "Observation:" marks the beginning of a tool's result, and you trust these results.

        You should not ask the human user for additional information, clarification, or context.
        If you cannot find a specific answer after exhausting available tools and approaches, you answer with Final Answer: inconclusive

        Question: {query}
        Thought:
        {transcript}

        """

        conversational_agent_prompt = """
As Weat, an intelligent food advisor, you assist users with inquiries related to dining out, cooking at home, and all aspects of food. Your responses are always well-informed, engaging, detailed and friendly. Avoid mentioning Google, Google reviews, or specific ratings and counts.

For each query, you should start your response in one of these ways:

1. "Final Answer:" - Use this to begin a direct, detailed response if you're certain about the answer.
2. If unsure or needing updated information, use your tools to gather current data. Indicate this process with:
   - "Thought:" followed by a brief explanation of your reasoning.
   - "Tool:" {tool_names} and on a new line, "Tool Input:" with the specific input for the tool WITHOUT quotation marks and should be presented separately on a new line.

The "Final Answer" is a comprehensive and informative answer with just enough details to the human user's question in a natual and friendly way. If the query from the user is vague, in the "Final Answer", you can seek additional details from the user if asking a question can help you serve the user better.
When giving "Final Answer", include referenced content IDs in JSON format at the end on a new line, deciding based on the conversation's flow whether to show these references to the user. Always set show_references to true if you use this reference the first time. Format: {{"references": {{[id_key_name]:[list of comma-seperated IDs]}},"show_references":true if based on the user's previous interactions you think the user is better to see the references; false if based on the user's previous interactions you think the user has already seen the references recently and doesn't to show the references again}}
When using tools, your observation of the tool's result is trusted and marked as "Observation:". 
Answer in the same language as the user's message.
Your message can potentially contain emoji to make it more lively and friendly.

You have access to these tools:
{tool_names_with_descriptions}

Below is the previous conversation between the user and you:
{memory}

Your response to a query should be structured as follows:
- Thought: [Your initial reasoning]
- Followed by either a direct answer i.e. "Final Answer" or tool usage details.

Question: {query}
Thought:
{transcript}
        """

        conversational_agent = ConversationalAgent(prompt_node=prompt_node, memory=summary_memory,
                                                   tools=[restaurant_description_tool],
                                                   prompt_template=conversational_agent_prompt)
        conversational_agent.final_answer_pattern = r"(?s)Final Answer\s*:\s*(.*)"

        return conversational_agent

    # def initialize_new_conversational_agent(self):
    #     document_store = PineconeDocumentStore(api_key='eb580754-c4c7-473d-9fcb-aa1d37c94a5c',
    #                                            similarity="cosine",
    #                                            embedding_dim=4096,
    #                                            environment="gcp-starter",
    #                                            index="business"
    #                                            )
    #
    #     retriever = EmbeddingRetriever(document_store=document_store,
    #                                    embedding_model="embed-english-v2.0",
    #                                    api_key="lfT5FlajkN9dFGO04V5hHcUkTPeNHmaA4uE1xwLw",
    #                                    model_format="cohere")
    #
    #     prompt = """You are an intelligent advisor called Weat helping a user with questions about restaurant, dining out, cooking at home
    #         and anything about food. The Query section is what a user talks to you. The Knowledge section is what your answer
    #         needs to based on. Give the answer in a natual, friendly, comprehensive and informative way. Don't mention any actual rating number and count
    #         in the answer.
    #
    #         Query: {query}\n
    #         Knowledge: {join(documents)}\n
    #         Answer:
    #         """
    #
    #     prompt_template = PromptTemplate(prompt=prompt,
    #                                      output_parser=AnswerParser())
    #
    #     prompt_node1 = PromptNode(model_name_or_path="gpt-4",
    #                               api_key="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",
    #                               default_prompt_template=prompt_template,
    #                               max_length=500)
    #
    #     query_pipeline = Pipeline()
    #     query_pipeline.add_node(component=retriever, name="Retriever", inputs=["Query"])
    #     query_pipeline.add_node(component=prompt_node1, name="PromptNode", inputs=["Retriever"])
    #
    #     model_name = "gpt-4"
    #     prompt_node = PromptNode(model_name, api_key="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",
    #                              max_length=256)
    #
    #     summary_memory = ConversationSummaryMemory(prompt_node)
    #
    #     qa_tool = Tool(name="Food_And_Restaurant_Consultant",
    #                    description="Useful for when you need to answer questions related to the restaurant, dining out and anything about food. ",
    #                    pipeline_or_node=query_pipeline,
    #                    output_variable="answers"
    #                    )
    #
    #     conversational_agent = ConversationalAgent(prompt_node=prompt_node, memory=summary_memory, tools=[qa_tool])
    #
    #     return conversational_agent
