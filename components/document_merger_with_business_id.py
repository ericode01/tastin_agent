from haystack.nodes import DocumentMerger
from haystack.schema import Document
from typing import Optional, List, Dict, Union, Any


class DocumentMergerWithBusinessId(DocumentMerger):

    def __init__(self, separator: str = " "):
        """
        :param separator: The separator that appears between subsequent merged documents.
        """
        super().__init__(separator)

    def merge(self, documents: List[Document], separator: Optional[str] = None) -> List[Document]:
        """
        Produce a list made up of a single document, which contains all the texts of the documents provided.

        :param documents: a list of Documents to merger together into one.
        :param separator: The separator that appears between subsequent merged documents.
        :return: List of Documents has a single merged document
        """
        if len(documents) == 0:
            raise ValueError("Document Merger needs at least one document to merge.")
        if not all(doc.content_type == "text" for doc in documents):
            raise ValueError(
                "Some of the documents provided are non-textual. Document Merger only works on textual documents."
            )

        separator = separator if separator is not None else self.separator

        merged_content = separator.join(
            ["Business_id:" + doc.meta["business_id"] + " Content:" + doc.content.replace("\n", " ") for doc in documents])
        common_meta = self._keep_common_keys([doc.meta for doc in documents])

        merged_document = Document(content=merged_content, meta=common_meta)
        return [merged_document]
