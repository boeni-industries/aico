"""Integration tests for AgencyGoalDependenciesRepository."""

import pytest
import uuid
from aico.data.agency.goal_models import AgencyGoalDependency
from datetime import datetime, UTC


class TestAgencyGoalDependenciesRepository:
    
    @pytest.mark.asyncio
    async def test_create_dependency(self, uow, test_user, test_goal):
        # Create prerequisite goal
        from aico.data.agency.models import Goal
        prereq_goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="test",
            goal_type="task",
            title="Prerequisite Goal",
            status="active",
            priority="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.goals.create(prereq_goal)
        await uow.commit()
        
        dependency = AgencyGoalDependency(
            dependency_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            prerequisite_goal_id=prereq_goal.goal_id,
            dependency_type="hard",
            active=True,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_goal_dependencies.create(dependency)
        await uow.commit()
        
        assert created.dependency_id == dependency.dependency_id
        assert created.dependency_type == "hard"
    
    @pytest.mark.asyncio
    async def test_get_dependency_by_id(self, uow, test_user, test_goal):
        from aico.data.agency.models import Goal
        prereq_goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="test",
            goal_type="task",
            title="Prerequisite Goal",
            status="active",
            priority="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.goals.create(prereq_goal)
        await uow.commit()
        
        dependency = AgencyGoalDependency(
            dependency_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            prerequisite_goal_id=prereq_goal.goal_id,
            dependency_type="soft",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_dependencies.create(dependency)
        await uow.commit()
        
        found = await uow.agency_goal_dependencies.get_by_id(dependency.dependency_id)
        assert found is not None
        assert found.dependency_type == "soft"
    
    @pytest.mark.asyncio
    async def test_update_dependency(self, uow, test_user, test_goal):
        from aico.data.agency.models import Goal
        prereq_goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="test",
            goal_type="task",
            title="Prerequisite Goal",
            status="active",
            priority="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.goals.create(prereq_goal)
        await uow.commit()
        
        dependency = AgencyGoalDependency(
            dependency_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            prerequisite_goal_id=prereq_goal.goal_id,
            dependency_type="hard",
            active=True,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_goal_dependencies.create(dependency)
        await uow.commit()
        
        created.active = False
        updated = await uow.agency_goal_dependencies.update(created.dependency_id, created)
        await uow.commit()
        
        assert updated.active is False
    
    @pytest.mark.asyncio
    async def test_delete_dependency(self, uow, test_user, test_goal):
        from aico.data.agency.models import Goal
        prereq_goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="test",
            goal_type="task",
            title="Prerequisite Goal",
            status="active",
            priority="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.goals.create(prereq_goal)
        await uow.commit()
        
        dependency = AgencyGoalDependency(
            dependency_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            prerequisite_goal_id=prereq_goal.goal_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_dependencies.create(dependency)
        await uow.commit()
        
        deleted = await uow.agency_goal_dependencies.delete(dependency.dependency_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_dependencies(self, uow, test_user):
        dependencies = await uow.agency_goal_dependencies.list(limit=10)
        assert isinstance(dependencies, list)
    
    @pytest.mark.asyncio
    async def test_count_dependencies(self, uow, test_user):
        count = await uow.agency_goal_dependencies.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_goal_dependencies(self, uow, test_user, test_goal):
        from aico.data.agency.models import Goal
        prereq_goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="test",
            goal_type="task",
            title="Prerequisite Goal",
            status="active",
            priority="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.goals.create(prereq_goal)
        await uow.commit()
        
        dep1 = AgencyGoalDependency(
            dependency_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            prerequisite_goal_id=prereq_goal.goal_id,
            active=True,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_dependencies.create(dep1)
        await uow.commit()
        
        deps = await uow.agency_goal_dependencies.get_goal_dependencies(test_goal.goal_id)
        assert len(deps) >= 1
