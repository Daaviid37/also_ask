#! /usr/bin/env python3
from .request.session import set_headers
from people_also_ask.google import (
    get_answer,
    generate_answer,
    get_simple_answer,
    get_related_questions,
    generate_related_questions,
)
