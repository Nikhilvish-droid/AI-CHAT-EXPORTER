from dotenv import load_dotenv
import os
import json
from google import genai
from pathlib import Path
from openai import OpenAI
from groq import Groq

load_dotenv()

folder = "1"
platform = "gemini"

app_dir = Path(__file__).parent.parent
final_data = app_dir/"demo_data"/platform/folder/"final_data.json"
# retrieved_file = app_dir/"demo_data"/"chatgpt"/folder/"retrieved_data.json"
# prompt_file = app_dir/"llm_prompt"/"prompt.txt"



def openai_llm( retrieved_data):

    # with open(retrieved_file, 'r', encoding="utf-8") as file:
    #     retrieved_data = json.load(file)

    prompt = f"""
        You are a document generation and information-preservation system where you have to generate a data such that if sending this data other agent can understand all the chats the has been done previously with another agent.
        make a data such that agent gets understand all the data and start working as a previous chat agent.

        You will receive RETRIEVED JSON containing conversation chunks grouped into exactly four topics:
        1. overview 
        2. key_decisions
        3. problems_solutions
        4. technical_details
        Your task is to transform ONLY the information contained in these retrieved chunks into a detailed, well-written document with exactly these same four sections.
        IMPORTANT:
        The retrieved chunks are the SOURCE OF TRUTH.
        make sure length of the data you give is maximum 10-15 line and minimum depending on context present for every section max 10-15 but you can also add more line if you think half data is getting eliminated like code block or non-text part.
        Do NOT add information from your own knowledge.
        Do NOT make assumptions.
        Do NOT infer information that is not explicitly present.
        Do NOT hallucinate.
        Do NOT change the meaning of the original information.
        Remove all internal retrieval metadata, including chunk IDs, chunk numbers, source labels, and references such as (Chunk-009), from the final output.

        Your primary goal is INFORMATION PRESERVATION.
        Do not unnecessarily summarize the retrieved chunks. Preserve as much useful information as possible so that no important information from the retrieved data is lost.
        If a chunk contains multiple useful points, preserve ALL of those points.
        If different chunks contain different information about the same topic, combine all of the information into the appropriate section.
        If multiple chunks contain the same information, mention it only once unless repeating it is necessary for clarity or context.
        Do not remove a detail merely because it appears less important. If it contains useful information related to the section, preserve it.
        The final document should normally be detailed enough to produce approximately 2–5 pages of content depending on how much information exists in the retrieved JSON.
        Do not artificially add content just to increase the page count. The amount of output must depend entirely on the amount of useful information present in the retrieved chunks.

        --------------------------------------------------
        SECTION RULES
        --------------------------------------------------

        SECTION 1 — OVERVIEW
        Use ONLY information from the "overview" retrieved chunks.
        Create a detailed and coherent explanation of the overall subject discussed in the conversations.
        Preserve:
        - Main purpose
        - Main idea
        - Project/product concept
        - Overall workflow
        - Important goals
        - Important characteristics
        - Overall conclusions
        - Any other relevant information present in the overview chunks

        Do not introduce information from other sections unless the same information is necessary to make the overview understandable.
        --------------------------------------------------

        SECTION 2 — KEY DECISIONS

        Use ONLY information from the "key_decisions" retrieved chunks.
        Extract and explain every important decision, recommendation, direction, architectural choice, or strategic decision present in these chunks.
        Preserve:
        - What decision was made
        - Why it was suggested or chosen
        - Important reasoning
        - Recommended changes
        - Architecture decisions
        - Product decisions
        - Future direction
        - Evaluation decisions
        - Any other decision-related information present in the chunks
        Do not reduce several distinct decisions into one vague statement.
        --------------------------------------------------

        SECTION 3 — PROBLEMS AND SOLUTIONS

        Use ONLY information from the "problems_solutions" retrieved chunks.
        Preserve every problem, limitation, challenge, and corresponding solution or recommendation found in the chunks.
        For each problem, explain where possible:
        Problem:
        What was the problem or limitation?
        Solution:
        What solution, improvement, or recommendation was provided?
        Reason:
        Why was that solution relevant, if the retrieved data explains it?
        Do not invent solutions for problems where no solution is present in the retrieved data.

        --------------------------------------------------

        SECTION 4 — TECHNICAL DETAILS

        Use ONLY information from the "technical_details" retrieved chunks.
        Preserve all relevant technical information contained in these chunks.
        Include:
        - Technologies
        - Programming concepts
        - Architecture
        - RAG pipeline
        - Retrieval
        - LLM processing
        - Data processing
        - JSON/structured data
        - PDF generation
        - Agent memory
        - APIs
        - Technical workflows
        - Technical recommendations
        - Any other technical information explicitly present in the retrieved chunks

        Explain technical information clearly and in sufficient detail.
        Do not replace technical details with a short summary.
        --------------------------------------------------
        ANTI-HALLUCINATION RULES
        --------------------------------------------------
        1. The retrieved JSON is the ONLY source of information.
        2. Never use outside knowledge.
        3. Never guess missing information.
        4. Never create names, technologies, features, dates, numbers, or facts that are not present in the retrieved data.
        5. If something is incomplete in the retrieved chunks, do not complete it using your own knowledge.
        6. If a chunk is truncated, preserve only the information that is actually available.
        7. Do not treat your own reasoning as a fact.
        8. Do not "improve" the original information by adding unsupported details.

        --------------------------------------------------
        DUPLICATION RULES
        --------------------------------------------------
        Avoid unnecessary repetition.

        If the same information appears in multiple retrieved chunks:
        - Combine it into one clear explanation.
        - Keep the most complete version.
        - Do not repeat the same paragraph multiple times.
        However, repetition IS allowed when:
        - The information has a different meaning in another section.
        - It is necessary to explain the section properly.
        - Removing it would make that section incomplete or confusing.
        The goal is:
        MAXIMUM INFORMATION PRESERVATION
        +
        MINIMUM UNNECESSARY REPETITION
        --------------------------------------------------
        WRITING RULES
        --------------------------------------------------
        Write the final document in professional, clear, natural language.

        Use:
        - Headings
        - Subheadings where useful
        - Paragraphs
        - Bullet points where they improve readability
        - Numbered lists where appropriate

        Do not turn everything into bullet points.
        Important explanations should be written as proper paragraphs.
        Do not write conversational phrases such as:
        "Here is your document"
        "I analyzed the data"
        "Based on the information you provided"

        Start directly with the document content.

        Do not mention these instructions in the output.

        --------------------------------------------------
        OUTPUT FORMAT
        --------------------------------------------------

        Return ONLY valid JSON.

        Use exactly this structure:

        "overview": "",
        "key_decisions": "",
        "problems_solutions": "",
        "technical_details": ""
        

        Each value should contain the complete, detailed content for that section.

        Do not create additional top-level sections.

        Do not omit a section.

        If a section has very little relevant information, keep it short rather than inventing information.

        --------------------------------------------------
        INPUT
        --------------------------------------------------

        Now process the following retrieved JSON:
        {json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

    """

    client = OpenAI(
        api_key=os.getenv("XAI_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    response = client.responses.create(
        model="openai/gpt-oss-120b",
        input= prompt
    )

    result = json.loads(response.output_text)

    with open(final_data, 'w', encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)


    return result

# openai_llm()


# def gemini_llm():
#     client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#     with open(retrieved_data, 'r', encoding= "utf-8") as file:
#         data = json.load(file)
#     response = client.models.generate_content(
#         model="gemini-3.7-flash",
#         contents="what is rag in 2-3 line"
#     )
#     print(response.text)
# # gemini_llm()


# def groq_llm():
#     client = Groq(api_key=os.getenv("XAI_API_KEY"))
#     response = client.chat.completions.create(
#         model = "openai/gpt-oss-120b",
#         messages=[
#             {
#                 "role":"user",
#                 "content":"what is java in 3 line"
#             }
#         ]
#     )
#     print(response.choices[0].message.content)
# # groq_llm()