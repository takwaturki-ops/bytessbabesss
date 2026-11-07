import random

from data_generation.generators import (SEED, generate_conversations, generate_customers, generate_fraud_scenarios,
                                        generate_orders_and_transactions)
from data_generation.validate_data import validate
from core import data


def _generate():
    rng = random.Random(SEED)
    cust = generate_customers(rng, 100)
    conv = generate_conversations(rng, cust, 150)
    orders, txns = generate_orders_and_transactions(rng, cust, conv, 100)
    fraud = generate_fraud_scenarios(rng, cust)
    return cust, conv, orders, txns, fraud


def test_generation_is_reproducible():
    assert _generate() == _generate()


def test_generated_files_validate():
    assert validate() == []


def test_counts_and_simulated_flag():
    cust, conv, orders, txns, fraud = _generate()
    assert (len(cust), len(conv), len(orders)) == (100, 150, 100)
    assert 40 <= len(fraud) <= 60
    assert all(r["simulated"] is True for r in cust + conv + orders + txns + fraud)


def test_dev_eval_splits_are_disjoint():
    dev = {c["conversation_id"] for c in data.split_records("conversations", "dev")}
    ev = {c["conversation_id"] for c in data.split_records("conversations", "eval")}
    assert dev and ev and not (dev & ev)
