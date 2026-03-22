from __future__ import annotations

from collections.abc import Mapping

from .openai_ig_catalogs import IG_CATEGORY_LABELS, IG_ROLE_LABELS
from .openai_system_prompts import (
    SYSTEM_PROMPT_IG_OPENAI_REQUEST,
    SYSTEM_PROMPT_REPUTATION_CREATOR_OPENAI_REQUEST,
    SYSTEM_PROMPT_REPUTATION_OPENAI_REQUEST,
)
from .templates import OpenAIRequestTemplate

IG_OPENAI_REQUEST = OpenAIRequestTemplate(
    system_prompt=SYSTEM_PROMPT_IG_OPENAI_REQUEST,
    model="gpt-5.4-nano-2026-03-17",
    text={
        "format": {
            "type": "json_schema",
            "name": "InstagramProfileAnalysisResponse",
            "strict": True,
            "schema": {
                "type": "object",
                "required": ["results"],
                "additionalProperties": False,
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/result"},
                        "minItems": 1,
                    }
                },
                "$defs": {
                    "result": {
                        "type": "object",
                        "required": ["username", "categories", "roles"],
                        "additionalProperties": False,
                        "properties": {
                            "username": {
                                "type": "string",
                                "minLength": 1,
                                "pattern": "^[A-Za-z0-9._]{1,30}$",
                            },
                            "categories": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 3,
                                "items": {
                                    "type": "string",
                                    "enum": list(IG_CATEGORY_LABELS),
                                },
                            },
                            "roles": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 2,
                                "items": {
                                    "type": "string",
                                    "enum": list(IG_ROLE_LABELS),
                                },
                            },
                        },
                    }
                },
            },
        }
    },
)

REPUTATION_OPENAI_REQUEST = OpenAIRequestTemplate(
    system_prompt=SYSTEM_PROMPT_REPUTATION_OPENAI_REQUEST,
    model="gpt-5.4-2026-03-05",
    tools=[{"type": "web_search"}],
    text={
        "format": {
            "type": "json_schema",
            "name": "ReputationCampaignStrategyResponse",
            "strict": True,
            "schema": {
                "type": "object",
                "required": [
                    "meta",
                    "assumptions",
                    "verified_facts",
                    "sections",
                    "kpis",
                    "influencer_plan",
                    "listening_reporting_plan",
                    "execution_roadmap",
                    "costs_summary",
                    "sources",
                ],
                "additionalProperties": False,
                "properties": {
                    "meta": {
                        "type": "object",
                        "required": [
                            "brand_name",
                            "brand_goals_type",
                            "timeframe",
                            "audience",
                            "campaign_type",
                            "web_research_used",
                            "notes_on_limits",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "brand_name": {"type": "string"},
                            "brand_goals_type": {"type": "string"},
                            "timeframe": {"type": "string"},
                            "audience": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "campaign_type": {"type": "string"},
                            "web_research_used": {"type": "boolean"},
                            "notes_on_limits": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "assumptions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["assumption", "why_needed", "risk_if_wrong"],
                            "additionalProperties": False,
                            "properties": {
                                "assumption": {"type": "string"},
                                "why_needed": {"type": "string"},
                                "risk_if_wrong": {"type": "string"},
                            },
                        },
                    },
                    "verified_facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["claim", "source_url"],
                            "additionalProperties": False,
                            "properties": {
                                "claim": {"type": "string"},
                                "source_url": {"type": "string"},
                            },
                        },
                    },
                    "sections": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["id", "title", "content"],
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                    "kpis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "category",
                                "kpi",
                                "definition",
                                "direction",
                                "cadence",
                            ],
                            "additionalProperties": False,
                            "properties": {
                                "category": {"type": "string"},
                                "kpi": {"type": "string"},
                                "definition": {"type": "string"},
                                "direction": {
                                    "type": "string",
                                    "enum": ["up", "down", "stable"],
                                },
                                "cadence": {
                                    "type": "string",
                                    "enum": ["weekly", "monthly"],
                                },
                            },
                        },
                    },
                    "influencer_plan": {
                        "type": "object",
                        "required": [
                            "recommended_now",
                            "rationale",
                            "shortlist",
                            "do_not_use_yet",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "recommended_now": {"type": "boolean"},
                            "rationale": {"type": "string"},
                            "shortlist": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": [
                                        "username",
                                        "role_in_strategy",
                                        "fit_rationale",
                                        "risks_or_red_flags",
                                        "suggested_deliverables",
                                        "measurement_notes",
                                    ],
                                    "additionalProperties": False,
                                    "properties": {
                                        "username": {"type": "string"},
                                        "role_in_strategy": {"type": "string"},
                                        "fit_rationale": {"type": "string"},
                                        "risks_or_red_flags": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "suggested_deliverables": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "measurement_notes": {"type": "string"},
                                    },
                                },
                            },
                            "do_not_use_yet": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["username", "why"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "username": {"type": "string"},
                                        "why": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "listening_reporting_plan": {
                        "type": "object",
                        "required": [
                            "keywords",
                            "channels",
                            "taxonomy",
                            "cadence",
                            "decision_rules",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "channels": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "taxonomy": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "cadence": {
                                "type": "object",
                                "required": [
                                    "monitoring",
                                    "weekly_report",
                                    "monthly_deep_dive",
                                ],
                                "additionalProperties": False,
                                "properties": {
                                    "monitoring": {"type": "string"},
                                    "weekly_report": {"type": "string"},
                                    "monthly_deep_dive": {"type": "string"},
                                },
                            },
                            "decision_rules": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "execution_roadmap": {
                        "type": "object",
                        "required": ["phases"],
                        "additionalProperties": False,
                        "properties": {
                            "phases": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": [
                                        "phase",
                                        "time_window",
                                        "goals",
                                        "key_actions",
                                        "owners",
                                    ],
                                    "additionalProperties": False,
                                    "properties": {
                                        "phase": {"type": "string"},
                                        "time_window": {"type": "string"},
                                        "goals": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "key_actions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "owners": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "costs_summary": {
                        "type": "object",
                        "required": [
                            "currency",
                            "provided_by_client",
                            "summary",
                            "summary_by_segment",
                            "cost_framework_if_missing",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "currency": {"type": ["string", "null"]},
                            "provided_by_client": {"type": "boolean"},
                            "summary": {
                                "type": "object",
                                "required": [
                                    "currency",
                                    "total_profiles",
                                    "classified_profiles",
                                    "unclassified_profiles",
                                    "total_min_mxn",
                                    "total_max_mxn",
                                    "total_average_mxn",
                                ],
                                "additionalProperties": False,
                                "properties": {
                                    "currency": {"type": ["string", "null"]},
                                    "total_profiles": {"type": "number"},
                                    "classified_profiles": {"type": "number"},
                                    "unclassified_profiles": {"type": "number"},
                                    "total_min_mxn": {"type": "number"},
                                    "total_max_mxn": {"type": "number"},
                                    "total_average_mxn": {"type": "number"},
                                },
                            },
                            "summary_by_segment": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": [
                                        "tier_key",
                                        "tier_label",
                                        "profiles_count",
                                        "typical_deliverable",
                                        "segment_min_mxn",
                                        "segment_max_mxn",
                                        "segment_average_mxn",
                                        "notes",
                                    ],
                                    "additionalProperties": False,
                                    "properties": {
                                        "tier_key": {"type": "string"},
                                        "tier_label": {"type": "string"},
                                        "profiles_count": {"type": "number"},
                                        "typical_deliverable": {
                                            "type": ["string", "null"]
                                        },
                                        "segment_min_mxn": {"type": "number"},
                                        "segment_max_mxn": {"type": "number"},
                                        "segment_average_mxn": {"type": "number"},
                                        "notes": {"type": ["string", "null"]},
                                    },
                                },
                            },
                            "cost_framework_if_missing": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type", "url", "used_for"],
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string"},
                                "url": {"type": "string"},
                                "used_for": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }
    },
)

CREATOR_OPENAI_REQUEST = OpenAIRequestTemplate(
    system_prompt=SYSTEM_PROMPT_REPUTATION_CREATOR_OPENAI_REQUEST,
    model="gpt-5.4-2026-03-05",
    tools=[{"type": "web_search"}],
    text={
        "format": {
            "type": "json_schema",
            "name": "ReputationCreatorStrategyResponse",
            "strict": True,
            "schema": {
                "type": "object",
                "required": [
                    "meta",
                    "assumptions",
                    "verified_facts",
                    "sections",
                    "kpis",
                    "execution_roadmap",
                    "sources",
                ],
                "additionalProperties": False,
                "properties": {
                    "meta": {
                        "type": "object",
                        "required": [
                            "creator_username",
                            "goal_type",
                            "timeframe",
                            "audience",
                            "primary_platforms",
                            "web_research_used",
                            "notes_on_limits",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "creator_username": {"type": "string"},
                            "goal_type": {"type": "string"},
                            "timeframe": {"type": "string"},
                            "audience": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "primary_platforms": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "web_research_used": {"type": "boolean"},
                            "notes_on_limits": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "assumptions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["assumption", "why_needed", "risk_if_wrong"],
                            "additionalProperties": False,
                            "properties": {
                                "assumption": {"type": "string"},
                                "why_needed": {"type": "string"},
                                "risk_if_wrong": {"type": "string"},
                            },
                        },
                    },
                    "verified_facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["claim", "source_url"],
                            "additionalProperties": False,
                            "properties": {
                                "claim": {"type": "string"},
                                "source_url": {"type": "string"},
                            },
                        },
                    },
                    "sections": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["id", "title", "content"],
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                    "kpis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "category",
                                "kpi",
                                "definition",
                                "direction",
                                "cadence",
                            ],
                            "additionalProperties": False,
                            "properties": {
                                "category": {"type": "string"},
                                "kpi": {"type": "string"},
                                "definition": {"type": "string"},
                                "direction": {
                                    "type": "string",
                                    "enum": ["up", "down", "stable"],
                                },
                                "cadence": {
                                    "type": "string",
                                    "enum": ["weekly", "monthly"],
                                },
                            },
                        },
                    },
                    "execution_roadmap": {
                        "type": "object",
                        "required": ["phases"],
                        "additionalProperties": False,
                        "properties": {
                            "phases": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": [
                                        "phase",
                                        "time_window",
                                        "goals",
                                        "key_actions",
                                        "owners",
                                    ],
                                    "additionalProperties": False,
                                    "properties": {
                                        "phase": {"type": "string"},
                                        "time_window": {"type": "string"},
                                        "goals": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "key_actions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "owners": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type", "url", "used_for"],
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string"},
                                "url": {"type": "string"},
                                "used_for": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }
    },
)

OPENAI_REQUEST_TEMPLATES: Mapping[str, OpenAIRequestTemplate] = {
    "instagram": IG_OPENAI_REQUEST,
    "reputation_campaign_strategy": REPUTATION_OPENAI_REQUEST,
    "reputation_creator_strategy": CREATOR_OPENAI_REQUEST,
}


def get_openai_request_template(name: str) -> OpenAIRequestTemplate:
    """
    Retrieve a preconfigured OpenAI request template by name.

    Raises:
        KeyError: If the template name is unknown.
    """

    try:
        return OPENAI_REQUEST_TEMPLATES[name]
    except KeyError as exc:
        available = ", ".join(sorted(OPENAI_REQUEST_TEMPLATES))
        raise KeyError(
            f"Unknown OpenAI request template '{name}'. Available: {available}"
        ) from exc


__all__ = [
    "IG_CATEGORY_LABELS",
    "IG_ROLE_LABELS",
    "IG_OPENAI_REQUEST",
    "REPUTATION_OPENAI_REQUEST",
    "CREATOR_OPENAI_REQUEST",
    "OPENAI_REQUEST_TEMPLATES",
    "get_openai_request_template",
]
