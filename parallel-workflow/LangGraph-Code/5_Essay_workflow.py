from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
import operator


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# 2. INITIALIZE LLM
# ============================================================

model = ChatOpenAI(
    model="gpt-4o-mini"
)


# ============================================================
# 3. DEFINE STRUCTURED OUTPUT SCHEMA
# ============================================================
# The LLM will return:
# {
#     "feedback": "...",
#     "score": 8
# }
#
# instead of returning unstructured text.

class EvaluationSchema(BaseModel):

    feedback: str = Field(
        description="Detailed feedback for the essay"
    )

    score: int = Field(
        description="Score out of 10",
        ge=0,
        le=10
    )


# Create a model that follows the EvaluationSchema
structured_model = model.with_structured_output(EvaluationSchema)


# ============================================================
# 4. ESSAY
# ============================================================

essay = """
Europe in the Age of AI: The Regulatory Superpower

As the world rushes headlong into the era of artificial intelligence,
the European Union finds itself playing a unique and complex role.
While the United States and China dominate the race to build the
largest foundation models and hardware ecosystems, Europe has
positioned itself as the global conscience of the AI age.

For Europe, the challenge is not simply about technological supremacy,
but about ensuring that AI aligns with democratic values, human rights,
and environmental sustainability.

Europe's strengths lie in its deep academic traditions and its
commitment to ethical frameworks. The continent is home to world-class
research hubs, producing some of the leading minds in machine learning.

Furthermore, Europe has a distinct advantage in industrial and B2B AI,
driven by its manufacturing powerhouses in Germany, France, and
Scandinavia.

However, Europe's most defining characteristic in this era is its
regulatory muscle. With the passage of the AI Act, the EU has created
the world's first comprehensive legal framework for artificial
intelligence, categorizing systems by risk and demanding unprecedented
transparency from tech companies.

The European vision for AI is heavily focused on public good and
sustainability. There is a strong push toward "Green AI", ensuring that
the massive energy consumption of data centers aligns with the
continent's aggressive climate goals.

In healthcare, European nations are leveraging AI to advance precision
medicine and streamline public health systems, while fiercely
protecting patient data.

Additionally, significant investments are being made to develop
open-source, multilingual AI models that preserve Europe's rich
linguistic diversity and reduce reliance on Silicon Valley.

Despite these noble ambitions, Europe faces substantial hurdles.
The continent suffers from a severe lack of hyperscale tech companies
and domestic cloud infrastructure, leaving it heavily dependent on
foreign technology.

This "compute deficit" is compounded by a fragmented venture capital
market, which often struggles to commercialize academic breakthroughs.

Consequently, Europe frequently experiences a brain drain, as its
brightest AI researchers are lured away by the massive salaries and
computing resources offered by American and Chinese tech giants.

The central tension for Europe is whether its regulatory approach will
foster "trustworthy AI" or stifle homegrown innovation.

Critics argue that stringent compliance burdens will price European
startups out of the market, relegating the continent to being a
consumer of foreign AI rather than a creator.

Proponents, however, believe that by setting global ethical standards
—the "Brussels Effect"—Europe will ultimately attract users and
enterprises that demand secure, unbiased, and privacy-respecting
technologies.

To succeed, Europe must balance its protective instincts with
aggressive investment in digital infrastructure and innovation.

It needs to foster a unified digital single market that allows startups
to scale across borders effortlessly, while also forging strategic
alliances to secure supply chains for critical hardware like
semiconductors.

In conclusion, Europe in the age of AI represents a profound
geopolitical experiment.

It is testing whether a society can successfully govern exponential
technology without sacrificing economic competitiveness.

If Europe succeeds, it will provide a desperately needed global
blueprint for human-centric AI; if it fails, it risks becoming an
over-regulated museum in a world driven by algorithmic innovation.
"""


# ============================================================
# 5. DEFINE LANGGRAPH STATE
# ============================================================
# State contains all the information that flows through the graph.

class EssayState(TypedDict):

    # Original essay
    essay: str

    # Feedback generated by individual evaluators
    language_feedback: str
    analysis_feedback: str
    clarity_feedback: str

    # Final summarized feedback
    overall_feedback: str

    # Individual scores from all evaluators
    #
    # operator.add tells LangGraph to APPEND/COMBINE
    # scores returned by different parallel nodes.
    individual_scores: Annotated[list[int], operator.add]

    # Final average score
    avg_score: float


# ============================================================
# 6. LANGUAGE EVALUATION NODE
# ============================================================

def evaluate_language(state: EssayState):

    prompt = f"""
    Evaluate the language quality of the following essay.

    Provide:
    1. Detailed feedback
    2. A score out of 10

    Essay:
    {state["essay"]}
    """

    # Call the structured LLM
    output = structured_model.invoke(prompt)

    # Return only the state fields that this node modifies
    return {
        "language_feedback": output.feedback,
        "individual_scores": [output.score]
    }


# ============================================================
# 7. ANALYSIS EVALUATION NODE
# ============================================================

def evaluate_analysis(state: EssayState):

    prompt = f"""
    Evaluate the depth and quality of analysis in the following essay.

    Provide:
    1. Detailed feedback
    2. A score out of 10

    Essay:
    {state["essay"]}
    """

    # Call the structured LLM
    output = structured_model.invoke(prompt)

    return {
        "analysis_feedback": output.feedback,
        "individual_scores": [output.score]
    }


# ============================================================
# 8. CLARITY EVALUATION NODE
# ============================================================

def evaluate_thought(state: EssayState):

    prompt = f"""
    Evaluate the clarity of thought and expression in the following essay.

    Provide:
    1. Detailed feedback
    2. A score out of 10

    Essay:
    {state["essay"]}
    """

    # Call the structured LLM
    output = structured_model.invoke(prompt)

    return {
        "clarity_feedback": output.feedback,
        "individual_scores": [output.score]
    }


# ============================================================
# 9. FINAL EVALUATION NODE
# ============================================================
# This node receives the outputs from all three evaluators.
#
# Because the three evaluator nodes run in parallel,
# LangGraph waits until all three have completed before
# executing this node.

def final_evaluation(state: EssayState):

    # Create a prompt using all three feedbacks
    prompt = f"""
    Based on the following evaluation feedbacks,
    create a summarized overall feedback for the essay.

    Language feedback:
    {state["language_feedback"]}

    Depth of analysis feedback:
    {state["analysis_feedback"]}

    Clarity of thought feedback:
    {state["clarity_feedback"]}
    """

    # Ask the normal LLM to summarize the feedback
    output = model.invoke(prompt)

    # Calculate average score
    avg_score = (
        sum(state["individual_scores"])
        / len(state["individual_scores"])
    )

    return {
        "overall_feedback": output.content,
        "avg_score": avg_score
    }


# ============================================================
# 10. CREATE LANGGRAPH
# ============================================================

graph = StateGraph(EssayState)


# ============================================================
# 11. ADD NODES
# ============================================================

graph.add_node(
    "evaluate_language",
    evaluate_language
)

graph.add_node(
    "evaluate_analysis",
    evaluate_analysis
)

graph.add_node(
    "evaluate_thought",
    evaluate_thought
)

graph.add_node(
    "final_evaluation",
    final_evaluation
)


# ============================================================
# 12. CREATE PARALLEL EDGES
# ============================================================
#
# START
#   ├──> Language Evaluation ──┐
#   ├──> Analysis Evaluation ──┼──> Final Evaluation ──> END
#   └──> Clarity Evaluation ───┘
#
# The three evaluation nodes can execute independently.

graph.add_edge(
    START,
    "evaluate_language"
)

graph.add_edge(
    START,
    "evaluate_analysis"
)

graph.add_edge(
    START,
    "evaluate_thought"
)


# ============================================================
# 13. CONNECT EVALUATION NODES TO FINAL NODE
# ============================================================

graph.add_edge(
    "evaluate_language",
    "final_evaluation"
)

graph.add_edge(
    "evaluate_analysis",
    "final_evaluation"
)

graph.add_edge(
    "evaluate_thought",
    "final_evaluation"
)


# ============================================================
# 14. CONNECT FINAL NODE TO END
# ============================================================

graph.add_edge(
    "final_evaluation",
    END
)


# ============================================================
# 15. COMPILE GRAPH
# ============================================================

workflow = graph.compile()


# ============================================================
# 16. INITIAL STATE
# ============================================================

initial_state = {
    "essay": essay,
    "language_feedback": "",
    "analysis_feedback": "",
    "clarity_feedback": "",
    "overall_feedback": "",
    "individual_scores": [],
    "avg_score": 0.0
}


# ============================================================
# 17. EXECUTE WORKFLOW
# ============================================================

final_state = workflow.invoke(initial_state)


# ============================================================
# 18. PRINT RESULTS
# ============================================================

print("\n========== LANGUAGE FEEDBACK ==========")
print(final_state["language_feedback"])

print("\n========== ANALYSIS FEEDBACK ==========")
print(final_state["analysis_feedback"])

print("\n========== CLARITY FEEDBACK ==========")
print(final_state["clarity_feedback"])

print("\n========== INDIVIDUAL SCORES ==========")
print(final_state["individual_scores"])

print("\n========== AVERAGE SCORE ==========")
print(final_state["avg_score"])

print("\n========== OVERALL FEEDBACK ==========")
print(final_state["overall_feedback"])