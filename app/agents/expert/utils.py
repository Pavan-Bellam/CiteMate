"""
Utility functions for the Expert Agent.

This module handles paper retrieval from S3 and conversion to markdown format.
Papers are stored in S3 as JSON (parsed by Unstructured.io) and converted to
clean markdown for LLM consumption.
"""

import os
import json
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.core.exceptions import PaperNotFoundError, PaperParseError


logger = get_logger(__name__, component="expert_utils")


# =============================================================================
# Markdown Conversion Helpers
# =============================================================================

def html_table_to_markdown(html_string: str) -> Optional[str]:
    """Convert an HTML table to markdown format."""
    soup = BeautifulSoup(html_string, 'html.parser')
    table = soup.find('table')

    if not table:
        return None

    rows = []

    # Get header
    thead = table.find('thead')
    if thead:
        header_cells = [th.get_text(strip=True) for th in thead.find_all('th')]
        if header_cells:
            rows.append('| ' + ' | '.join(header_cells) + ' |')
            rows.append('| ' + ' | '.join(['---'] * len(header_cells)) + ' |')

    # Get body
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append('| ' + ' | '.join(cells) + ' |')

    return '\n'.join(rows) if rows else None


def element_to_markdown(unit: Dict[str, Any]) -> str:
    """Convert a single element to markdown based on its type."""
    element_type = unit.get('type', 'UncategorizedText')
    text = unit.get('text', '').strip()
    metadata = unit.get('metadata', {})

    if element_type == 'Image':
        return ''

    if element_type == 'Table':
        html_table = metadata.get('text_as_html')
        if html_table:
            md_table = html_table_to_markdown(html_table)
            if md_table:
                return f'\n{md_table}\n\n'
        # Fallback to code block if HTML parsing fails
        if text:
            return f'\n```\n{text}\n```\n\n'
        return ''

    if not text:
        return ''

    match element_type:
        case 'Title':
            return f'# {text}\n\n'
        case 'Header':
            return f'## {text}\n\n'
        case 'ListItem':
            return f'- {text}\n'
        case 'CodeSnippet':
            return f'```\n{text}\n```\n\n'
        case 'FigureCaption':
            return f'*{text}*\n\n'
        case 'Footer':
            return f'<sub>{text}</sub>\n\n'
        case _:  # NarrativeText, UncategorizedText
            return f'{text}\n\n'


def convert_to_markdown(data: List[Dict[str, Any]]) -> str:
    """Convert parsed paper data to markdown format.

    Processes a list of document elements (from Unstructured.io JSON) and
    converts them to a clean markdown document with proper formatting.
    """
    lines = []
    current_page = None
    prev_type = None

    for unit in data:
        page = unit.get('metadata', {}).get('page_number')
        element_type = unit.get('type', '')

        # Page breaks
        if page and page != current_page:
            current_page = page
            lines.append(f'\n---\n<!-- Page {current_page} -->\n\n')

        # Handle list grouping (consecutive ListItems shouldn't have gaps)
        if element_type == 'ListItem' and prev_type != 'ListItem':
            lines.append('\n')

        lines.append(element_to_markdown(unit))
        prev_type = element_type

    return ''.join(lines)


# =============================================================================
# S3 Operations
# =============================================================================

def get_parsed_from_s3(s3_client, s3_bucket: str, s3_prefix: str, paper_id: str) -> List[Dict[str, Any]]:
    """Retrieve parsed paper JSON from S3.

    Args:
        s3_client: Boto3 S3 client.
        s3_bucket: S3 bucket name.
        s3_prefix: Prefix path where papers are stored.
        paper_id: ArXiv paper ID.

    Returns:
        Parsed document elements as a list of dictionaries.

    Raises:
        PaperNotFoundError: If paper doesn't exist in S3.
    """
    s3_key = f"{s3_prefix}/raw/{paper_id}.json"
    logger.debug("Fetching paper from S3", extra={"paper_id": paper_id, "s3_key": s3_key})

    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        file_content = response['Body'].read().decode('utf-8')
        return json.loads(file_content)

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise PaperNotFoundError(paper_id=paper_id, source="S3")
        logger.error("S3 error", extra={"paper_id": paper_id, "error": str(e)})
        raise


# =============================================================================
# Public API
# =============================================================================

def get_markdown_of_paper(paper_id: str) -> str:
    """Retrieve a paper from S3 and convert it to markdown.

    This is the main entry point for getting paper content. It fetches the
    parsed JSON from S3 and converts it to clean markdown for LLM consumption.

    Args:
        paper_id: ArXiv paper ID (e.g., "2512.02942v1").

    Returns:
        Paper content as a markdown string.

    Raises:
        PaperNotFoundError: If paper doesn't exist in S3.
        PaperParseError: If markdown conversion fails.
    """
    s3_client = boto3.client('s3')
    s3_bucket = os.environ['BOOTSTRAP_BUCKET_NAME']
    s3_prefix = os.environ['PAPERS_S3_PREFIX']

    raw_data = get_parsed_from_s3(s3_client, s3_bucket, s3_prefix, paper_id)

    try:
        return convert_to_markdown(raw_data)
    except Exception as e:
        logger.error("Markdown conversion failed", extra={"paper_id": paper_id, "error": str(e)})
        raise PaperParseError(paper_id=paper_id, reason=str(e)) from e
