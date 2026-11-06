import datetime
import yaml
from rag_packages.contracts.dto.shared_dto import BaseDTO
from rag_packages.contracts.dto.chat import ChatMessage
from pydantic import Field


class RewrittenQuery(BaseDTO):
    queries: list[str] | None = Field(default_factory=list)
    fromDate: str | None = None
    toDate: str | None = None


def parse_rewritten_user_query(rewritten_query: str) -> RewrittenQuery:
    # TODO: remove this so the argument above is used
    rewritten_query = '{"queries":["electricity bills","electricity invoices","electric utility billing statements","power supply bills","electricity charges and billing records","electricity consumption statements"],"fromDate":null,"toDate":null}'

    return RewrittenQuery.model_validate_json(rewritten_query)


# build prompt to be sent to the assistant with document context and related instructions
def build_prompt_with_context(
    prompt: str, document_context: str, rewritten_prompt: str | None = None
) -> str:
    user_prompt_snippet = f"## User Question\n\n{prompt}\n"
    rewritten_prompt_snippet = f"### Rewritten Prompt\n\n{rewritten_prompt}\n"

    updated_prompt = f"""
{user_prompt_snippet if prompt else ""}
{rewritten_prompt_snippet if rewritten_prompt else ""}
## Context

### Very Important

---

#### File Instructions

If there are files that are somewhat relevant to the user's question, reference them and ensure to add the links for each of them.
Sort these files from the newest to the oldest.
If there are tens of somewhat relevant files their links can be embedded as markdown links of the form [{{file name}}]({{file url}}).

#### Date Context

The current date and time is: {datetime.datetime.now(tz=datetime.UTC).isoformat()}.
If asked about a month, day, or year, use the current date and time to provide an accurate answer.
If no year is specified, use the current year, {datetime.datetime.now(tz=datetime.UTC).year}.
If no month is specified, use the current month, {datetime.datetime.now(tz=datetime.UTC).month}.

### Retrieved Knowledge

The following information comes from a knowledge base. Use it to answer the question.
You should not reference retrieved documents in general terms, but instead use the information to provide a specific and relevant answer.
If a specific answer is from one or more specific documents and you need to reference them, you should provide the document name and / or file URL in your answer.

{document_context}
### Closing Context

Prefer newer information and always respect the date context specified above.
Prefer structuring data as lists instead of tables, and avoid using tables unless necessary.
Be as detailed and accurate as possible with a focus on the most salient information.
"""
    return updated_prompt


def build_rewrite_prompt(
    user_prompt: str, prev_conversation: list[ChatMessage] | None = None
) -> str:
    prev_snippet = f"Previous Conversation: \n{yaml.dump(prev_conversation)}"

    rewrite = f"""
## Convert the user's request into a JSON object for vector database search.

Return a valid JSON object with exactly these three keys:

- `"queries"`: an array of 5–12 distinct semantic search query strings.
- `"fromDate"`: an ISO 8601 UTC date-time string representing the start of the requested date range, inclusive, or `null` if it cannot be determined.
- `"toDate"`: an ISO 8601 UTC date-time string representing the end of the requested date range, inclusive, or `null` if it cannot be determined.

### Date interpretation rules

Use the current date as the reference point for resolving relative dates. Interpret dates accurately according to the following rules:

1. **Last year:** Use the entire previous calendar year, from January 1 at 00:00:00.000 UTC to December 31 at 23:59:59.999 UTC.

2. **This year:** Use the entire current calendar year.

3. **Next year:** Use the entire next calendar year.

4. **Last month:** Use the entire previous calendar month, from its first day at 00:00:00.000 UTC to its last day at 23:59:59.999 UTC.

5. **This month:** Use the entire current calendar month, from its first day at 00:00:00.000 UTC to its last day at 23:59:59.999 UTC.

6. **Next month:** Use the entire next calendar month.

7. **Specific month and year:** If the user mentions a month and year, such as "electricity invoices for March 2025", use the first and last days of that month and year.

8. **Specific month without a year:** If the user mentions a month without specifying a year, such as "electricity invoices for March", interpret it as the most recent occurrence of that month, including the current month if it matches. Use that month's full date range.

9. **Relative month references:** Interpret phrases such as "two months ago", "three months ago", "previous month", "past month", "last 3 months", and "next 3 months" according to their natural meaning. For a number of complete calendar months, calculate the appropriate start and end dates. For example, "last 3 months" means the previous three complete calendar months, excluding the current month.

10. **Specific dates and date ranges:** When the user provides exact dates, use the specified dates. When only a start or end date is provided, infer the other boundary only if the intended period is clear; otherwise, use `null` for the uncertain field.

11. **Year-to-date:** For requests such as "this year so far" or "year to date", set `fromDate` to January 1 of the current year and `toDate` to the current date and time.

12. **Month-to-date:** For requests such as "this month so far", set `fromDate` to the first day of the current month and `toDate` to the current date and time.

13. **No date specified:** If the user does not specify or imply a time period, set both `fromDate` and `toDate` to `null`. Do not assume a date range based solely on the current date.

14. **Ambiguous dates:** If a date or date range cannot be reliably determined, use `null` for the uncertain field rather than inventing dates.

### Query generation rules

1. Generate 5–12 distinct semantic search query strings that express the user's original intent in different ways.
2. Preserve the requested subject, document type, and purpose. For example, an electricity invoice request should generate variations involving electricity invoices, electricity bills, utility billing statements, electricity charges, and power supply bills.
3. Include the relevant year in some queries when a year is known.
4. For month-based requests, include the relevant month and year in some queries.
5. Do not include individual day numbers or exact date ranges in the query strings unless the user explicitly asks to search for a specific date.
6. Avoid redundant queries, unrelated concepts, and unnecessary variations that do not improve semantic retrieval.
7. Do not put the date filters themselves into the `queries` array as structured data. The `fromDate` and `toDate` fields handle date filtering separately.

### Output requirements

1. Return only a raw JSON object. Do not include Markdown code fences, explanations, comments, or any other text.
2. The JSON object must contain exactly the keys `"queries"`, `"fromDate"`, and `"toDate"`.
3. Use double quotes for all JSON keys and string values.
4. Ensure the response is valid JSON that can be parsed immediately using `JSON.parse()`.
5. Do not include trailing commas, additional keys, or text outside the JSON object.
6. Format all non-null dates as UTC ISO 8601 date-time strings with millisecond precision, such as `"2025-03-01T00:00:00.000Z"`.

### Example

Assume the current date is October 23, 2026, and the user asks: "Can you give me the electricity invoices for last month?"

Return exactly:

{{
  "queries": [
    "electricity invoices from last month",
    "electricity bills for September 2026",
    "electricity utility invoices issued in September 2026",
    "electricity billing statements from September 2026",
    "power supply invoices for September 2026",
    "electricity consumption bills from September 2026"
  ],
  "fromDate": "2026-09-01T00:00:00.000Z",
  "toDate": "2026-09-30T23:59:59.999Z"
}}

User request: {user_prompt}

{prev_snippet if prev_conversation else ""}

"""
    return rewrite
