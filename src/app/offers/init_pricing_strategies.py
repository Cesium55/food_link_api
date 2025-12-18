"""
Initializer for pricing strategies.
Creates default pricing strategies with their steps.
"""

from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.offers.models import PricingStrategy, PricingStrategyStep


# Constants for time calculations (in seconds)
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800


async def init_pricing_strategies(session: AsyncSession) -> Dict[str, PricingStrategy]:
    """
    Initialize default pricing strategies.
    Creates strategies if they don't exist (idempotent).
    
    Args:
        session: Database session
    """
    # Strategy 1: "Последняя неделя" (Last Week)
    last_week_strategy = await _get_or_create_strategy(
        session, 
        name="Последняя неделя",
        steps=[
            {"time_remaining_seconds": 7 * SECONDS_PER_DAY, "discount_percent": 30.0},
            {"time_remaining_seconds": 6 * SECONDS_PER_DAY, "discount_percent": 40.0},
            {"time_remaining_seconds": 5 * SECONDS_PER_DAY, "discount_percent": 50.0},
            {"time_remaining_seconds": 4 * SECONDS_PER_DAY, "discount_percent": 60.0},
            {"time_remaining_seconds": 3 * SECONDS_PER_DAY, "discount_percent": 70.0},
            {"time_remaining_seconds": 2 * SECONDS_PER_DAY, "discount_percent": 80.0},
            {"time_remaining_seconds": 1 * SECONDS_PER_DAY, "discount_percent": 90.0},
        ]
    )
    
    # Strategy 2: "Мягкое снижение" (Soft Reduction)
    soft_reduction_strategy = await _get_or_create_strategy(
        session,
        name="Мягкое снижение",
        steps=[
            {"time_remaining_seconds": 14 * SECONDS_PER_DAY, "discount_percent": 10.0},
            {"time_remaining_seconds": 10 * SECONDS_PER_DAY, "discount_percent": 20.0},
            {"time_remaining_seconds": 7 * SECONDS_PER_DAY, "discount_percent": 30.0},
            {"time_remaining_seconds": 4 * SECONDS_PER_DAY, "discount_percent": 40.0},
            {"time_remaining_seconds": 2 * SECONDS_PER_DAY, "discount_percent": 50.0},
            {"time_remaining_seconds": 1 * SECONDS_PER_DAY, "discount_percent": 60.0},
        ]
    )
    
    await session.flush()
    
    # Reload strategies with steps to avoid lazy loading issues
    last_week_reloaded_result = await session.execute(
        select(PricingStrategy)
        .where(PricingStrategy.id == last_week_strategy.id)
        .options(selectinload(PricingStrategy.steps))
    )
    last_week_reloaded = last_week_reloaded_result.scalar_one()
    
    soft_reduction_reloaded_result = await session.execute(
        select(PricingStrategy)
        .where(PricingStrategy.id == soft_reduction_strategy.id)
        .options(selectinload(PricingStrategy.steps))
    )
    soft_reduction_reloaded = soft_reduction_reloaded_result.scalar_one()
    
    await session.commit()
    
    return {
        "last_week": last_week_reloaded,
        "soft_reduction": soft_reduction_reloaded
    }


async def _get_or_create_strategy(
    session: AsyncSession,
    name: str,
    steps: list[dict]
) -> PricingStrategy:
    """
    Get existing strategy by name or create new one with steps.
    
    Args:
        session: Database session
        name: Strategy name
        steps: List of step dictionaries with time_remaining_seconds and discount_percent
        
    Returns:
        PricingStrategy instance
    """
    # Check if strategy already exists
    result = await session.execute(
        select(PricingStrategy).where(PricingStrategy.name == name)
    )
    strategy = result.scalar_one_or_none()
    
    if strategy:
        # Strategy exists, check if steps need to be updated
        # For simplicity, we'll recreate steps if they don't match
        existing_steps_result = await session.execute(
            select(PricingStrategyStep)
            .where(PricingStrategyStep.strategy_id == strategy.id)
            .order_by(PricingStrategyStep.time_remaining_seconds)
        )
        existing_steps = existing_steps_result.scalars().all()
        
        # Compare steps count
        if len(existing_steps) != len(steps):
            # Delete existing steps and create new ones
            await session.execute(
                delete(PricingStrategyStep).where(PricingStrategyStep.strategy_id == strategy.id)
            )
            await _create_steps(session, strategy.id, steps)
        else:
            # Check if steps match (simple comparison)
            steps_match = all(
                existing_steps[i].time_remaining_seconds == steps[i]["time_remaining_seconds"]
                and existing_steps[i].discount_percent == steps[i]["discount_percent"]
                for i in range(len(steps))
            )
            if not steps_match:
                # Delete and recreate steps
                await session.execute(
                    delete(PricingStrategyStep).where(PricingStrategyStep.strategy_id == strategy.id)
                )
                await _create_steps(session, strategy.id, steps)
    else:
        # Create new strategy
        strategy = PricingStrategy(name=name)
        session.add(strategy)
        await session.flush()  # Get the ID
        
        # Create steps
        await _create_steps(session, strategy.id, steps)
    
    return strategy


async def _create_steps(
    session: AsyncSession,
    strategy_id: int,
    steps: list[dict]
) -> None:
    """
    Create pricing strategy steps.
    
    Args:
        session: Database session
        strategy_id: Strategy ID
        steps: List of step dictionaries with time_remaining_seconds and discount_percent
    """
    for step_data in steps:
        step = PricingStrategyStep(
            strategy_id=strategy_id,
            time_remaining_seconds=step_data["time_remaining_seconds"],
            discount_percent=step_data["discount_percent"]
        )
        session.add(step)
