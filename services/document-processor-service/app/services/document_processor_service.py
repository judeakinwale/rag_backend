from pathlib import Path
import asyncio
import base64
import logging
from tempfile import NamedTemporaryFile
from typing import Any, Literal, TypeAlias
from pydantic import Field
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument, TableItem, PictureItem, BoundingBox
from docling_core.transforms.chunker import DocChunk
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document as LangChainDocument
from packages.rag_packages.src.rag_packages.contracts.dto.shared_dto import BaseDTO


logger = logging.getLogger(__name__)

FileType = Literal[
    "pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "bmp"
]
FILE_TYPES = {"pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "bmp"}

MdHeaderSplitter: TypeAlias = MarkdownHeaderTextSplitter
CharSplitter: TypeAlias = RecursiveCharacterTextSplitter

ChunkStrategy: TypeAlias = Literal["docling", "markdown"]


class ChunkDetails(BaseDTO):
    pages: list[int] = Field(default_factory=list)
    headings: list[str] = Field(default_factory=list)
    captions: list[str] = Field(default_factory=list)
    tables: list[TableItem] = Field(default_factory=list)
    figures: list[PictureItem] = Field(default_factory=list)
    bbox: list[BoundingBox] = Field(default_factory=list)


class ProcessedChunk(BaseDTO):
    index: int
    text: str
    details: ChunkDetails | None = None
    metadata: dict[str, Any] | None = None


class ProcessedDocumentDTO(BaseDTO):
    file_name: str | None = None
    file_type: FileType
    markdown: str
    chunks: list[ProcessedChunk]


class DocumentProcessor:
    def __init__(
        self,
        header_splitter: MdHeaderSplitter | None = None,
        char_splitter: CharSplitter | None = None,
    ):
        self.converter = DocumentConverter()
        self.header_splitter = header_splitter
        self.char_splitter = char_splitter
        self.chunker = HybridChunker()

    def _get_splitters(
        self, chunk_size: int = 1000, chunk_overlap: int = 200, **kwargs
    ) -> tuple[MdHeaderSplitter, CharSplitter]:
        if self.header_splitter is None:
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                # ("####", "Header 4"),
            ]
            self.header_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on, **kwargs
            )

        if self.char_splitter is None:
            self.char_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                # the first two separators are for headings and in this case, redundant
                separators=["\n# ", "\n## ", "\n\n", "\n", " ", ""],
            )

        return self.header_splitter, self.char_splitter

    def _clear_splitters(self) -> bool:
        self.header_splitter = None
        self.char_splitter = None
        return True

    def _get_file_binary(self, file_b64: str) -> bytes:
        try:
            return base64.b64decode(file_b64, validate=True)
        except Exception as e:
            raise ValueError("Invalid base64 input") from e

    def _create_temporary_file(self, file: bytes, file_type: FileType) -> Path:
        if file_type not in FILE_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        with NamedTemporaryFile(
            mode="wb", delete=False, suffix=f".{file_type}"
        ) as temp_file:
            temp_file.write(file)
            return Path(temp_file.name)

    def _remove_temporary_file(self, path: Path):
        try:
            path.unlink(missing_ok=True)
            # os.remove(path)
        except Exception:
            logger.exception("Error removing temporary file")

    def _get_processed_langchain_md_chunk_with_metadata(
        self, doc: LangChainDocument, index: int
    ) -> ProcessedChunk:
        metadata = doc.metadata

        # [metadata.get("Header 1")]
        # for deterministic ordering of heading, sort the keys first.
        # should not be a problem since insertion order is preserved
        headings = [
            v
            for k, v in metadata.items()
            if isinstance(k, str) and k.startswith("Header") and v is not None
        ]
        details = ChunkDetails(headings=headings)
        return ProcessedChunk(
            index=index,
            text=doc.page_content,
            details=details,
            metadata=metadata,
        )

    def _get_processed_doc_chunk_with_metadata(
        self, chunk: DocChunk, index: int
    ) -> ProcessedChunk:
        details = self.get_doc_chunk_details(chunk)
        metadata = chunk.meta.model_dump(
            exclude={"doc_items", "headings"},
            exclude_unset=True,
            exclude_none=True,
        )
        return ProcessedChunk(
            index=index,
            text=chunk.text,
            details=details,
            metadata=metadata,
        )

    @staticmethod
    def get_doc_chunk_details(chunk: DocChunk) -> ChunkDetails:
        doc_items = chunk.meta.doc_items
        headings = chunk.meta.headings
        captions = chunk.meta.captions

        tables: list[TableItem] = []
        figures: list[PictureItem] = []
        pages_set: set[int] = set()
        bbox: list[BoundingBox] = []

        for item in doc_items:
            if isinstance(item, TableItem):
                tables.append(item)

            elif isinstance(item, PictureItem):
                figures.append(item)

            for prov_item in item.prov:
                prov_page_no = prov_item.page_no
                prov_bbox = prov_item.bbox
                pages_set.add(prov_page_no)
                bbox.append(prov_bbox)

        pages = sorted(pages_set)
        if pages:
            logger.info(
                f"chunk headings and page: {headings}, {pages[0]} - {pages[-1]}"
            )

        details = ChunkDetails(
            pages=pages,
            headings=headings,
            captions=captions,
            tables=tables,
            figures=figures,
            bbox=bbox,
        )
        return details

    def extract_text(
        self,
        file_b64: str,
        file_type: FileType,
        # file_name: str | None = None,
    ) -> tuple[str, DoclingDocument]:
        file_path: Path | None = None
        try:
            file_binary = self._get_file_binary(file_b64)
            file_path = self._create_temporary_file(file_binary, file_type)

            result = self.converter.convert(file_path)
            document = result.document
            markdown = document.export_to_markdown()

            return markdown, document

        finally:
            if file_path is not None:
                self._remove_temporary_file(file_path)

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[ProcessedChunk]:
        header_splitter, char_splitter = self._get_splitters(chunk_size, chunk_overlap)

        header_chunks = header_splitter.split_text(text)
        chunks = char_splitter.split_documents(header_chunks)

        processed_chunks = [
            self._get_processed_langchain_md_chunk_with_metadata(chunk, i)
            for i, chunk in enumerate(chunks)
        ]
        return processed_chunks

    def chunk_document(
        self,
        document: DoclingDocument,
    ) -> list[ProcessedChunk]:
        chunks = self.chunker.chunk(document)

        processed_chunks = [
            self._get_processed_doc_chunk_with_metadata(chunk, i)
            for i, chunk in enumerate(chunks)
        ]
        return processed_chunks

    async def process(
        self,
        file_b64: str,
        file_type: FileType,
        file_name: str | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        chunk_strategy: ChunkStrategy = "docling",
    ) -> ProcessedDocumentDTO:

        text, document = await asyncio.to_thread(self.extract_text, file_b64, file_type)

        processed_chunks: list[ProcessedChunk]
        match chunk_strategy:
            case "docling":
                processed_chunks = await asyncio.to_thread(
                    self.chunk_document,
                    document,
                )
            case "markdown":
                processed_chunks = await asyncio.to_thread(
                    self.chunk_text,
                    text,
                    chunk_size,
                    chunk_overlap,
                )
            case _:
                raise ValueError(f"Invalid chunk strategy: {chunk_strategy}")

        return ProcessedDocumentDTO(
            file_name=file_name,
            file_type=file_type,
            markdown=text,
            chunks=processed_chunks,
        )

    def close(self):
        self._clear_splitters()
