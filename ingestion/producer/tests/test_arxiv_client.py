"""Integration tests for ArxivClient."""

import pytest

from src.arxiv_client import ArxivClient


@pytest.fixture
def arxiv_client():
    with ArxivClient() as client:
        yield client


class TestFetchPapers:
    def test_returns_paper_metadata(self, arxiv_client: ArxivClient):
        papers = list(arxiv_client.fetch_papers(category="cs.LG", max_results=1))

        assert len(papers) == 1

        paper = papers[0]
        assert "arxiv_id" in paper
        assert "title" in paper
        assert "authors" in paper
        assert "abstract" in paper
        assert "pdf_url" in paper
        assert "published" in paper
        assert "categories" in paper

    def test_respects_max_results(self, arxiv_client: ArxivClient):
        papers = list(arxiv_client.fetch_papers(category="cs.LG", max_results=3))

        assert len(papers) == 3

    def test_pdf_url_is_valid(self, arxiv_client: ArxivClient):
        papers = list(arxiv_client.fetch_papers(category="cs.LG", max_results=1))

        assert papers[0]["pdf_url"].startswith("http")
        assert "arxiv.org" in papers[0]["pdf_url"]


class TestDownloadPdf:
    def test_downloads_valid_pdf(self, arxiv_client: ArxivClient):
        papers = list(arxiv_client.fetch_papers(category="cs.LG", max_results=1))
        pdf_bytes = arxiv_client.download_pdf(papers[0]["pdf_url"])

        # PDF files start with %PDF magic bytes
        assert pdf_bytes[:4] == b"%PDF"

    def test_raises_on_invalid_url(self, arxiv_client: ArxivClient):
        with pytest.raises(Exception):
            arxiv_client.download_pdf("https://arxiv.org/pdf/invalid.pdf")
