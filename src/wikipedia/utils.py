import wikipediaapi

wiki_wiki = wikipediaapi.Wikipedia(
    user_agent='MovieDB (antoine-marie.michelozzi@etu.unice.fr)',
    language='fr',
    extract_format=wikipediaapi.ExtractFormat.WIKI
)

def extract_section_text(section):
    text = section.text or ""
    for subsection in section.sections:
        text += "\n" + extract_section_text(subsection)
    return text

def get_wikipedia_section(section_name, page_title):
    page = wiki_wiki.page(page_title)
    if not page.exists():
        return None

    section = page.section_by_title(section_name)
    if section:
        return extract_section_text(section).strip()

    summary = (page.summary or "").strip()
    return summary or None