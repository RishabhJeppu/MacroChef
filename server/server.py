# import httpx
import os
import serpapi
import urllib.request
import urllib.parse
import re
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()
serpapi_key = os.getenv("SERPAPI_KEY")

client = serpapi.Client(api_key=serpapi_key)

mcp = FastMCP("recipes")


def make_google_request(query: str) -> dict:
    """Make a request to the Google API to get recipes"""
    result = client.search(
        q=f"{query} recipes -site:youtube.com -site:instagram.com -site:facebook.com -site:tiktok.com -site:pinterest.com -site:twitter.com",
        engine="google",
        location="United States",
        hl="en",
        max_results=1,
    )

    extracted_results = []
    if "organic_results" in result:
        for r in result["organic_results"]:
            extracted_results.append({"title": r["title"], "link": r["link"]})
            break
    return {"recipes_results": extracted_results}


@mcp.tool()
def search_youtube_vides(query: str) -> str:
    """Search for videos on YouTube to get recipes

    Args:
        query (str): The query to search for

    Returns:
        str: The URL of the first video
    """
    query += " recipes"
    search_query = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={search_query}"
    html = urllib.request.urlopen(url).read().decode()
    video_ids = re.findall(r"watch\?v=(\S{11})", html)
    return "https://www.youtube.com/watch?v=" + video_ids[0]


def scrape_recipe(url: str) -> dict:
    """Scrapes a recipe from a given URL and returns a structured recipe."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return {"error": str(e)}

    soup = BeautifulSoup(response.text, "html.parser")

    recipe = {
        "title": soup.find("h1").get_text(strip=True)
        if soup.find("h1")
        else "No Title Found",
        "text": soup.get_text(separator="\n", strip=True),
    }
    return recipe


@mcp.tool()
def get_recipe(query: str) -> str:
    """Get a recipe from a given query

    Args:
        query (str): The query to search for

    Returns:
        str: The recipe
    """
    search_results = make_google_request(query)
    if search_results and search_results.get("recipes_results"):
        first_recipe = search_results["recipes_results"][0]
        first_recipe_link = first_recipe.get("link")
        if not first_recipe_link:
            return "No recipe link found in search results."

        scraped_recipe = scrape_recipe(first_recipe_link)
        if "error" in scraped_recipe:
            return f"Error scraping recipe: {scraped_recipe['error']}"

        title = scraped_recipe.get("title", "No Title Found")
        content = scraped_recipe.get("text", "")

        return f"{title}\n\n{content}"
    else:
        return "No recipe found"
