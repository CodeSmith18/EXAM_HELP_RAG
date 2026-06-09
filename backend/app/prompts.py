from __future__ import annotations

SYSTEM_RAG_RULES = """
You are ExamPrep RAG, an exam preparation assistant.
Use only the retrieved PDF context.
If the answer is not present in the context, say it was not found in the uploaded PDF.
Do not invent facts, page numbers, citations, examples, or marks.
Keep language simple, exam-friendly, and concise.
"""


MCQ_GENERATION_PROMPT = """
Generate {num_questions} {difficulty} MCQ questions from the PDF context.
Topic filter: {topic}

Rules:
- Use only the context below.
- Each MCQ must have exactly 4 options.
- Exactly one option must be correct.
- The correct_answer must match one option text exactly.
- Include a short explanation from the context.
- Return valid JSON only.

JSON shape:
{{
  "questions": [
    {{
      "type": "mcq",
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer": "...",
      "explanation": "..."
    }}
  ]
}}

PDF context:
{context}
"""


WRITTEN_QUESTION_PROMPT = """
Generate {num_questions} {difficulty} written-answer exam questions from the PDF context.
Topic filter: {topic}

Rules:
- Use only the context below.
- Questions should be answerable from the context.
- Include a model_answer and a rubric with correctness, completeness, and clarity points.
- Return valid JSON only.

JSON shape:
{{
  "questions": [
    {{
      "type": "written",
      "question": "...",
      "model_answer": "...",
      "rubric": ["correctness: ...", "completeness: ...", "clarity: ..."]
    }}
  ]
}}

PDF context:
{context}
"""


MIXED_TEST_PROMPT = """
Generate {num_questions} {difficulty} mixed exam questions from the PDF context.
Topic filter: {topic}

Rules:
- Use only the context below.
- Include a balanced mix of MCQ and written questions.
- MCQs must have exactly 4 options and one correct answer.
- Written questions must include a model_answer and rubric.
- Return valid JSON only.

JSON shape:
{{
  "questions": [
    {{
      "type": "mcq",
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer": "...",
      "explanation": "..."
    }},
    {{
      "type": "written",
      "question": "...",
      "model_answer": "...",
      "rubric": ["correctness: ...", "completeness: ...", "clarity: ..."]
    }}
  ]
}}

PDF context:
{context}
"""


WRITTEN_EVALUATION_PROMPT = """
Evaluate the student's written answer using only the PDF context.

Question:
{question}

Student answer:
{student_answer}

Rules:
- Score out of 10.
- Award marks only for content supported by the PDF context.
- Penalize unsupported or hallucinated claims.
- Give concise feedback.
- Return valid JSON only.

JSON shape:
{{
  "score": 0,
  "feedback": "...",
  "model_answer": "...",
  "rubric_breakdown": {{
    "correctness": "...",
    "completeness": "...",
    "clarity": "..."
  }}
}}

PDF context:
{context}
"""


STUDY_MODE_PROMPT = """
Explain the topic in simple exam-friendly language using only the PDF context.

Topic:
{topic}

Rules:
- If the topic is not found, clearly say it was not found in the uploaded PDF.
- Include simple_explanation, key_points, example, important_terms, and quick_revision_summary.
- If a diagram helps and the context supports it, include a Mermaid diagram string.
- The Mermaid diagram must be plain Mermaid syntax, not Markdown fenced code.
- Return valid JSON only.

JSON shape:
{{
  "simple_explanation": "...",
  "key_points": ["...", "..."],
  "example": "...",
  "important_terms": [
    {{"term": "...", "meaning": "..."}}
  ],
  "quick_revision_summary": "...",
  "mermaid_diagram": "flowchart TD\\nA[Concept] --> B[Detail]"
}}

PDF context:
{context}
"""


MERMAID_DIAGRAM_PROMPT = """
Create a Mermaid diagram only when the PDF context clearly supports a process, flow, hierarchy, or relationship.

Topic:
{topic}

Rules:
- Use only the PDF context.
- Return valid JSON only.
- If a diagram is not useful, return null for mermaid_diagram.

JSON shape:
{{
  "mermaid_diagram": "flowchart TD\\nA[Start] --> B[Next]"
}}

PDF context:
{context}
"""


GENERAL_QA_PROMPT = """
Answer the question using only the PDF context.

Question:
{question}

Rules:
- If the answer is missing, say: "The answer was not found in the uploaded PDF."
- Do not use outside knowledge.
- Return valid JSON only.

JSON shape:
{{
  "answer": "..."
}}

PDF context:
{context}
"""
