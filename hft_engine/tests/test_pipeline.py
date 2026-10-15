import asyncio

import pytest

from core.constants import SIDE_BUY, SIDE_SELL
from core.firehose import Firehose
from core.metrics import EngineMetrics
from core.ring_buffer import RingBuffer
from engine.limit_order_book import LimitOrderBook


def test_firehose_buffer_round_trip_and_clean_shutdown(tmp_path):
    path = tmp_path / "pipeline.rb"
    metrics = EngineMetrics()
    with RingBuffer(path, capacity=256) as rb:
        producer = Firehose(rb, metrics, target_ops=6400)
        asyncio.run(producer.run(duration=0.025))
        sent = metrics.snapshot()["orders_sent"]
        book = LimitOrderBook()
        orders = []
        trades = []
        while not rb.is_empty():
            order = rb.get()
            orders.append(order)
            trades.extend(book.submit(order))

    assert sent == len(orders)
    assert sent > 0
    assert [order.order_id for order in orders] == list(range(sent))
    assert all(order.side in (SIDE_BUY, SIDE_SELL) for order in orders)
    assert all(order.quantity > 0 and order.price > 0 for order in orders)
    assert book.total_orders == sent
    assert book.total_trades == len(trades)


def test_firehose_rejects_invalid_parameters():
    metrics = EngineMetrics()
    for target, error in [(0, ValueError), (-1, ValueError), (True, TypeError)]:
        with pytest.raises(error):
            Firehose(None, metrics, target_ops=target)


def test_firehose_stop_ends_a_long_run_promptly(tmp_path):
    async def run_until_stopped(producer):
        task = asyncio.create_task(producer.run(duration=30))
        await asyncio.sleep(0.01)
        producer.stop()
        await asyncio.wait_for(task, timeout=1)

    with RingBuffer(tmp_path / "stoppable.rb", capacity=256) as rb:
        producer = Firehose(rb, EngineMetrics(), target_ops=6400)
        asyncio.run(run_until_stopped(producer))


@pytest.mark.parametrize("duration", [0, -1, float("inf"), float("nan")])
def test_firehose_rejects_invalid_duration(duration):
    with pytest.raises(ValueError):
        asyncio.run(Firehose(None, EngineMetrics()).run(duration=duration))


def test_empty_metrics_are_safe():
    metrics = EngineMetrics()
    snapshot = metrics.snapshot()
    assert snapshot["enqueue_rate"] == 0
    assert snapshot["dequeue_rate"] == 0
    assert snapshot["latency"]["avg"] == 0
    assert snapshot["latency"]["p99"] == 0


@pytest.mark.parametrize("sample", [-1, float("inf"), float("nan")])
def test_latency_metrics_reject_invalid_samples(sample):
    metrics = EngineMetrics()
    with pytest.raises(ValueError):
        metrics.match_latency.record_ns(sample)
