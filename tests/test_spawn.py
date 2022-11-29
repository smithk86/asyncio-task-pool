import asyncio

import pytest

from asyncio_pool import AsyncioPool, AsyncioPoolWorker

from .utils import (
    exception_worker,
    worker_1,
    worker_args,
    worker_ids,
    worker_long,
    workers,
)

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize("worker", workers, ids=worker_ids)
async def test_spawn(worker: AsyncioPoolWorker[int]) -> None:
    async with AsyncioPool(1000) as pool:
        future = pool.spawn(worker, 5)
        test = await future
        assert test == 5


async def test_spawn_task_name() -> None:
    async with AsyncioPool(2) as pool:
        # pool is empty
        assert pool.is_empty is True
        assert pool.is_full is False

        future = pool.spawn(worker_long, 5)

        # pool is not full or empty
        assert pool.is_empty is False
        assert pool.is_full is False

        pool.spawn(worker_long, 0)
        pool.spawn(worker_long, 0)

        # pool is full
        assert pool.is_empty is False
        assert pool.is_full is True

        await asyncio.sleep(0.5)

        # 2 running tasks; task 3 is pending
        assert len(pool) == 3
        assert len(pool.running_tasks()) == 2
        assert [t.get_name() for t in pool.running_tasks()] == [
            "AsyncioPool-worker_long",
            "AsyncioPool-worker_long",
        ]

        await asyncio.sleep(0.75)

        # final task is running
        assert len(pool) == 1
        assert len(pool.running_tasks()) == 1
        assert [t.get_name() for t in pool.running_tasks()] == [
            "AsyncioPool-worker_long"
        ]

        # validate the return value for the first task
        test = await future
        assert test == 5

    # pool is empty
    assert pool.is_empty is True
    assert pool.is_full is False


async def test_spawn_with_kwargs() -> None:
    async with AsyncioPool(1000) as pool:
        result = await pool.spawn(worker_args, 5, "123")
        assert result == (5, "123", 123, None)

        result = await pool.spawn(worker_args, 1337, "test", kw1=1337, kw2="test")
        assert result == (1337, "test", 1337, "test")


@pytest.mark.parametrize("worker", workers, ids=worker_ids)
async def test_spawn_exit_with_active_tasks(worker: AsyncioPoolWorker[int]) -> None:
    async with AsyncioPool(1000) as pool:
        future = pool.spawn(worker, 5)
        assert future.done() is False

    assert future.done() is True


async def test_spawn_inactive() -> None:
    async with AsyncioPool(1000) as pool:
        pass

    with pytest.raises(
        RuntimeError, match="This task pool is not active; no new tasks can be started."
    ):
        pool.spawn(worker_1, 5)


async def test_spawn_with_exception() -> None:
    async with AsyncioPool(2) as pool:
        future = pool.spawn(exception_worker, range(5))
        with pytest.raises(RuntimeError, match="task failed"):
            await future