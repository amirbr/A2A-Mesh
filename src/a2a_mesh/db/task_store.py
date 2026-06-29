"""Postgres-backed A2A TaskStore implementation."""

import logging

from a2a.server.context import ServerCallContext
from a2a.server.tasks import TaskStore
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse, Task
from google.protobuf import json_format
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a2a_mesh.db.models.task import TaskRecord
from a2a_mesh.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _serialize(task: Task) -> str:
    return json_format.MessageToJson(task, preserving_proto_field_name=True)


def _deserialize(data: str) -> Task:
    task = Task()
    json_format.Parse(data, task)
    return task


def _state_name(task: Task) -> str:
    descriptor = Task.DESCRIPTOR.fields_by_name["status"].message_type
    state_field = descriptor.fields_by_name["state"]
    return state_field.enum_type.values_by_number[task.status.state].name.lower()


class PostgresTaskStore(TaskStore):
    """Persists A2A tasks to Postgres.

    Stores the full Task proto as JSON in the `data` column.
    Indexes task_id, context_id, agent_id, and state for fast lookups.
    """

    def __init__(self, agent_id: str) -> None:
        self._agent_id = agent_id

    async def _session(self) -> AsyncSession:
        return AsyncSessionLocal()

    async def save(self, task: Task, context: ServerCallContext) -> None:
        """Insert or update a task row."""
        state = _state_name(task)
        data = _serialize(task)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                existing = await session.get(TaskRecord, task.id)
                if existing:
                    existing.state = state
                    existing.data = data
                else:
                    session.add(
                        TaskRecord(
                            id=task.id,
                            context_id=task.context_id,
                            agent_id=self._agent_id,
                            state=state,
                            data=data,
                        )
                    )
        logger.debug("Saved task %s (state=%s)", task.id, state)

    async def get(self, task_id: str, context: ServerCallContext) -> Task | None:
        """Retrieve a task by ID."""
        async with AsyncSessionLocal() as session:
            record = await session.get(TaskRecord, task_id)
            if record is None:
                return None
            return _deserialize(record.data)

    async def list(
        self,
        params: ListTasksRequest,
        context: ServerCallContext,
    ) -> ListTasksResponse:
        """List tasks for this agent."""
        async with AsyncSessionLocal() as session:
            stmt = select(TaskRecord).where(TaskRecord.agent_id == self._agent_id)
            result = await session.execute(stmt)
            records = result.scalars().all()
            tasks = [_deserialize(r.data) for r in records]
            return ListTasksResponse(tasks=tasks)

    async def delete(self, task_id: str, context: ServerCallContext) -> None:
        """Delete a task by ID."""
        async with AsyncSessionLocal() as session:
            async with session.begin():
                record = await session.get(TaskRecord, task_id)
                if record:
                    await session.delete(record)
