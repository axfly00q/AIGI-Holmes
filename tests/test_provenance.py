from backend.services.provenance import extract_publication_metadata


def test_extract_jsonld_publication_date_as_reliable():
    html = """
    <html><head>
      <title>Example news</title>
      <script type="application/ld+json">
        {"@type":"NewsArticle","datePublished":"2024-05-01T10:30:00Z"}
      </script>
    </head><body></body></html>
    """

    meta = extract_publication_metadata(html)

    assert meta["title"] == "Example news"
    assert meta["date_evidence"] == "reliable"
    assert meta["date_source"] == "JSON-LD datePublished"
    assert meta["published_at"].year == 2024
    assert meta["published_at"].month == 5


def test_extract_search_date_as_reference_when_page_has_no_date():
    meta = extract_publication_metadata("<html><body>No date</body></html>", "2024-06-02")

    assert meta["date_evidence"] == "reference"
    assert meta["date_source"] == "搜索摘要日期"
    assert meta["published_at"].day == 2
