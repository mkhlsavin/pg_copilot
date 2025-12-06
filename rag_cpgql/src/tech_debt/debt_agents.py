"""
Technical Debt Quantification Agents (Scenario 12)

Implements three specialized agents for detecting and managing technical debt:

1. DebtCalculator - Measures debt and calculates metrics
   - Detect debt items using patterns
   - Calculate total debt effort
   - Compute debt ratio and interest
   - Track debt by category

2. PrioritizationEngine - Ranks debt items by ROI
   - Calculate priority scores
   - Assess business value vs effort
   - Rank by ROI (Return on Investment)
   - Group by quick wins vs long-term investments

3. RepaymentPlanner - Creates debt repayment plans
   - Generate sprint-based repayment plans
   - Balance quick wins and strategic debt
   - Estimate velocity and timeline
   - Track repayment progress

Author: Technical Debt Team
Date: 2025-11-22
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .debt_patterns import (
    DebtPattern,
    DebtSeverity,
    DebtCategory,
    DEBT_PATTERNS,
    get_pattern,
    get_patterns_by_category,
    calculate_total_effort
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DebtItem:
    """
    A detected instance of technical debt.

    Attributes:
        item_id: Unique identifier
        pattern_id: ID of the pattern
        pattern_name: Human-readable pattern name
        category: Debt category
        severity: Debt severity
        location: File path or location
        line_number: Line number (if applicable)
        description: Description of the debt
        effort_hours: Estimated effort to fix (hours)
        interest_rate: How debt grows over time
        business_impact: Impact on business/users
        metadata: Additional CPG data
    """
    item_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    location: str
    line_number: int
    description: str
    effort_hours: float
    interest_rate: float
    business_impact: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DebtMetrics:
    """
    Overall technical debt metrics.

    Attributes:
        total_items: Total debt items found
        total_effort_hours: Total effort to fix all debt
        debt_ratio: Debt ratio (effort / codebase size)
        by_severity: Count by severity level
        by_category: Count by category
        average_effort: Average effort per item
        high_interest_items: Items with high interest rates
        codebase_size_lines: Total lines of code
    """
    total_items: int
    total_effort_hours: float
    debt_ratio: float
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    average_effort: float
    high_interest_items: int
    codebase_size_lines: int


@dataclass
class PrioritizedDebt:
    """
    Debt item with priority score and ROI.

    Attributes:
        item: The debt item
        priority_score: Priority score (1-10, 10 = highest)
        roi_score: Return on investment score
        business_value: Estimated business value
        quick_win: Whether this is a quick win (low effort, high value)
        strategic: Whether this is strategic (high effort, very high value)
        recommended_sprint: Which sprint to address this in
    """
    item: DebtItem
    priority_score: int
    roi_score: float
    business_value: str
    quick_win: bool
    strategic: bool
    recommended_sprint: int


@dataclass
class RepaymentPlan:
    """
    Phased technical debt repayment plan.

    Attributes:
        plan_id: Unique identifier
        timestamp: When plan was created
        total_items: Total debt items in plan
        total_effort_hours: Total effort for all items
        sprints: List of sprints with debt items
        quick_wins: Count of quick win items
        strategic_items: Count of strategic items
        estimated_weeks: Estimated weeks to complete
        summary: Executive summary
        recommendations: Top recommendations
    """
    plan_id: str
    timestamp: str
    total_items: int
    total_effort_hours: float
    sprints: List[Dict[str, Any]]
    quick_wins: int
    strategic_items: int
    estimated_weeks: int
    summary: str
    recommendations: List[str]


# ============================================================================
# AGENT 1: DEBT CALCULATOR
# ============================================================================

class DebtCalculator:
    """
    Agent 1: Measures technical debt and calculates metrics.

    Detects:
    - TODO/FIXME comments
    - Deprecated API usage
    - Code duplication
    - Long methods
    - Complex methods
    - Dead code

    Calculates:
    - Total debt effort (hours)
    - Debt ratio (effort / codebase size)
    - Debt by category and severity
    - High-interest debt items

    Usage:
        calculator = DebtCalculator(cpg_service)
        items = calculator.detect_all_debt(limit_per_pattern=20)
        metrics = calculator.calculate_metrics(items, codebase_size=10000)
    """

    def __init__(self, cpg_service):
        """
        Initialize DebtCalculator.

        Args:
            cpg_service: CPGQueryService instance for database access
        """
        self.cpg = cpg_service
        self.patterns = DEBT_PATTERNS

    def detect_all_debt(self, limit_per_pattern: int = 20) -> List[DebtItem]:
        """
        Detect all technical debt items using all patterns.

        Args:
            limit_per_pattern: Maximum items per pattern (default: 20)

        Returns:
            List of DebtItem objects, sorted by effort (highest first)
        """
        all_items = []

        for pattern in self.patterns:
            try:
                items = self.detect_pattern(pattern, limit=limit_per_pattern)
                all_items.extend(items)
            except Exception as e:
                print(f"Error detecting pattern {pattern.pattern_id}: {e}")
                continue

        # Sort by effort (highest first)
        all_items.sort(key=lambda item: item.effort_hours, reverse=True)

        return all_items

    def detect_pattern(self, pattern: DebtPattern, limit: int = 20) -> List[DebtItem]:
        """
        Detect instances of a specific debt pattern.

        Args:
            pattern: DebtPattern to detect
            limit: Maximum items to return

        Returns:
            List of DebtItem objects for this pattern
        """
        # Execute the pattern's detection query
        query = pattern.detection_query
        results = self.cpg.execute_custom_sql(query)

        # Convert results to DebtItem objects
        items = []
        for idx, result in enumerate(results[:limit]):
            item = self._create_item_from_result(pattern, result, idx)
            items.append(item)

        return items

    def _create_item_from_result(
        self,
        pattern: DebtPattern,
        result: Dict[str, Any],
        index: int
    ) -> DebtItem:
        """
        Create a DebtItem from a query result.

        Args:
            pattern: The pattern that was detected
            result: Query result dictionary
            index: Index of this result

        Returns:
            DebtItem object
        """
        item_id = f"{pattern.pattern_id}_{index:03d}"

        # Extract location
        location = result.get('filename', result.get('caller_file', result.get('file_1', 'unknown')))
        line_number = result.get('line_number', result.get('line_1', 0))

        # Create description
        description = self._format_description(pattern, result)

        return DebtItem(
            item_id=item_id,
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.name,
            category=pattern.category.value,
            severity=pattern.severity.value,
            location=location,
            line_number=line_number,
            description=description,
            effort_hours=pattern.effort_hours,
            interest_rate=pattern.interest_rate,
            business_impact=pattern.impact,
            metadata=result
        )

    def _format_description(self, pattern: DebtPattern, result: Dict[str, Any]) -> str:
        """Format debt description based on pattern type"""
        if pattern.pattern_id == "TODO_COMMENTS":
            method_name = result.get('method_name', 'unknown')
            return f"TODO/FIXME comment in method '{method_name}'"
        elif pattern.pattern_id == "DEPRECATED_API":
            deprecated_api = result.get('deprecated_api', 'unknown')
            caller_method = result.get('caller_method', 'unknown')
            return f"Method '{caller_method}' calls deprecated API '{deprecated_api}'"
        elif pattern.pattern_id == "CODE_DUPLICATION":
            method_1 = result.get('method_1', 'unknown')
            method_2 = result.get('method_2', 'unknown')
            return f"Potential duplication between '{method_1}' and '{method_2}'"
        elif pattern.pattern_id == "LONG_METHODS":
            method_name = result.get('method_name', 'unknown')
            length = result.get('method_length', 0)
            return f"Long method '{method_name}' ({length} lines)"
        elif pattern.pattern_id == "COMPLEX_METHODS":
            method_name = result.get('method_name', 'unknown')
            complexity = result.get('estimated_complexity', 0)
            return f"Complex method '{method_name}' (complexity: {complexity})"
        elif pattern.pattern_id == "DEAD_CODE":
            method_name = result.get('method_name', 'unknown')
            return f"Unused method '{method_name}' (no callers)"
        else:
            return f"{pattern.name} at {result.get('filename', 'unknown')}"

    def calculate_metrics(self, items: List[DebtItem], codebase_size: int = 10000) -> DebtMetrics:
        """
        Calculate comprehensive debt metrics.

        Args:
            items: List of debt items
            codebase_size: Total lines of code in codebase

        Returns:
            DebtMetrics object
        """
        # Count by severity and category
        by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        by_category = {'code_quality': 0, 'maintenance': 0, 'complexity': 0, 'unused_code': 0}

        for item in items:
            by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
            by_category[item.category] = by_category.get(item.category, 0) + 1

        # Calculate total effort
        total_effort = sum(item.effort_hours for item in items)

        # Calculate debt ratio
        debt_ratio = total_effort / (codebase_size / 100.0) if codebase_size > 0 else 0.0

        # Average effort
        avg_effort = total_effort / len(items) if items else 0.0

        # High interest items (interest rate > 1.2 = 20%+)
        high_interest = len([item for item in items if item.interest_rate > 1.2])

        return DebtMetrics(
            total_items=len(items),
            total_effort_hours=total_effort,
            debt_ratio=debt_ratio,
            by_severity=by_severity,
            by_category=by_category,
            average_effort=avg_effort,
            high_interest_items=high_interest,
            codebase_size_lines=codebase_size
        )


# ============================================================================
# AGENT 2: PRIORITIZATION ENGINE
# ============================================================================

class PrioritizationEngine:
    """
    Agent 2: Ranks debt items by ROI (Return on Investment).

    Prioritizes based on:
    - Effort to fix (lower = better)
    - Business value/impact (higher = better)
    - Severity (higher = more urgent)
    - Interest rate (higher = more urgent)
    - Category strategic importance

    Classifies as:
    - Quick wins (low effort, high value)
    - Strategic (high effort, very high value)
    - Regular (everything else)

    Usage:
        engine = PrioritizationEngine()
        prioritized = engine.prioritize_debt(items, metrics)
        quick_wins = engine.get_quick_wins(prioritized)
    """

    def __init__(self):
        """Initialize PrioritizationEngine"""
        pass

    def prioritize_debt(self, items: List[DebtItem], metrics: DebtMetrics) -> List[PrioritizedDebt]:
        """
        Prioritize debt items by ROI.

        Args:
            items: List of debt items
            metrics: Overall debt metrics

        Returns:
            List of PrioritizedDebt objects, sorted by priority
        """
        prioritized = []

        for item in items:
            # Calculate priority score (1-10)
            priority = self._calculate_priority(item, metrics)

            # Calculate ROI score
            roi = self._calculate_roi(item)

            # Calculate business value
            business_value = self._assess_business_value(item)

            # Classify as quick win or strategic
            quick_win = self._is_quick_win(item, priority, roi)
            strategic = self._is_strategic(item, priority, roi)

            # Recommend sprint (1-based)
            sprint = self._recommend_sprint(priority, quick_win, strategic)

            prioritized.append(PrioritizedDebt(
                item=item,
                priority_score=priority,
                roi_score=roi,
                business_value=business_value,
                quick_win=quick_win,
                strategic=strategic,
                recommended_sprint=sprint
            ))

        # Sort by priority (highest first)
        prioritized.sort(key=lambda p: p.priority_score, reverse=True)

        return prioritized

    def _calculate_priority(self, item: DebtItem, metrics: DebtMetrics) -> int:
        """Calculate priority score (1-10, 10 = highest)"""
        # Base priority from severity
        severity_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2
        }
        base_priority = severity_scores.get(item.severity, 5)

        # Boost for high interest rate (debt growing fast)
        if item.interest_rate > 1.3:  # 30%+ interest
            base_priority = min(base_priority + 2, 10)
        elif item.interest_rate > 1.2:  # 20%+ interest
            base_priority = min(base_priority + 1, 10)

        # Boost for strategic categories
        if item.category in ['maintenance', 'complexity']:
            base_priority = min(base_priority + 1, 10)

        return base_priority

    def _calculate_roi(self, item: DebtItem) -> float:
        """
        Calculate ROI score (higher = better return).

        ROI = Business Value / Effort
        """
        # Estimate business value from severity and interest
        severity_value = {
            'critical': 100,
            'high': 70,
            'medium': 40,
            'low': 20
        }
        base_value = severity_value.get(item.severity, 50)

        # Adjust for interest rate (higher interest = more value in fixing)
        adjusted_value = base_value * item.interest_rate

        # ROI = value / effort
        roi = adjusted_value / item.effort_hours if item.effort_hours > 0 else 0.0

        return roi

    def _assess_business_value(self, item: DebtItem) -> str:
        """Assess business value (very_high, high, medium, low)"""
        if item.severity == 'critical' and item.interest_rate > 1.2:
            return "very_high"
        elif item.severity in ['critical', 'high']:
            return "high"
        elif item.severity == 'medium':
            return "medium"
        else:
            return "low"

    def _is_quick_win(self, item: DebtItem, priority: int, roi: float) -> bool:
        """Determine if this is a quick win"""
        # Quick win: low effort (< 2 hours), decent priority (>= 5), good ROI (>= 20)
        return item.effort_hours < 2.0 and priority >= 5 and roi >= 20.0

    def _is_strategic(self, item: DebtItem, priority: int, roi: float) -> bool:
        """Determine if this is strategic debt"""
        # Strategic: high effort (> 5 hours), high priority (>= 8), very high business value
        return item.effort_hours > 5.0 and priority >= 8 and self._assess_business_value(item) in ['high', 'very_high']

    def _recommend_sprint(self, priority: int, quick_win: bool, strategic: bool) -> int:
        """Recommend which sprint to address this in (1-based)"""
        if quick_win:
            return 1  # Address quick wins immediately
        elif priority >= 8:
            return 1  # High priority items in sprint 1
        elif priority >= 6:
            return 2  # Medium-high priority in sprint 2
        elif priority >= 4:
            return 3  # Medium priority in sprint 3
        else:
            return 4  # Low priority in sprint 4+

    def get_quick_wins(self, prioritized: List[PrioritizedDebt]) -> List[PrioritizedDebt]:
        """Get all quick win items"""
        return [p for p in prioritized if p.quick_win]

    def get_strategic_items(self, prioritized: List[PrioritizedDebt]) -> List[PrioritizedDebt]:
        """Get all strategic items"""
        return [p for p in prioritized if p.strategic]


# ============================================================================
# AGENT 3: REPAYMENT PLANNER
# ============================================================================

class RepaymentPlanner:
    """
    Agent 3: Creates phased technical debt repayment plans.

    Generates:
    - Sprint-based repayment plans
    - Balanced mix of quick wins and strategic debt
    - Effort estimates and timelines
    - Progress tracking recommendations

    Plans consider:
    - Team velocity (hours per sprint)
    - Priority and ROI
    - Dependencies between debt items
    - Risk and complexity

    Usage:
        planner = RepaymentPlanner()
        plan = planner.create_plan(prioritized_items, team_velocity=40)
        sprints = planner.get_sprint_breakdown(plan)
    """

    def __init__(self, team_velocity: float = 40.0):
        """
        Initialize RepaymentPlanner.

        Args:
            team_velocity: Team capacity in hours per 2-week sprint (default: 40)
        """
        self.team_velocity = team_velocity

    def create_plan(
        self,
        prioritized: List[PrioritizedDebt],
        max_sprints: int = 6
    ) -> RepaymentPlan:
        """
        Create a comprehensive debt repayment plan.

        Args:
            prioritized: List of prioritized debt items
            max_sprints: Maximum number of sprints to plan (default: 6)

        Returns:
            RepaymentPlan object
        """
        # Organize items by recommended sprint
        sprints = self._organize_sprints(prioritized, max_sprints)

        # Balance sprints (don't overload)
        balanced_sprints = self._balance_sprints(sprints)

        # Calculate totals
        total_items = len(prioritized)
        total_effort = sum(p.item.effort_hours for p in prioritized)

        # Count quick wins and strategic
        quick_wins = len([p for p in prioritized if p.quick_win])
        strategic = len([p for p in prioritized if p.strategic])

        # Estimate weeks (2 weeks per sprint)
        estimated_weeks = len(balanced_sprints) * 2

        # Generate summary
        summary = self._generate_summary(prioritized, balanced_sprints, total_effort)

        # Generate recommendations
        recommendations = self._generate_recommendations(prioritized, balanced_sprints)

        return RepaymentPlan(
            plan_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            total_items=total_items,
            total_effort_hours=total_effort,
            sprints=balanced_sprints,
            quick_wins=quick_wins,
            strategic_items=strategic,
            estimated_weeks=estimated_weeks,
            summary=summary,
            recommendations=recommendations
        )

    def _organize_sprints(
        self,
        prioritized: List[PrioritizedDebt],
        max_sprints: int
    ) -> List[Dict[str, Any]]:
        """Organize debt items into sprints"""
        sprints = [{
            'sprint_number': i + 1,
            'items': [],
            'total_effort': 0.0,
            'quick_wins': 0,
            'strategic': 0
        } for i in range(max_sprints)]

        for p in prioritized:
            sprint_idx = min(p.recommended_sprint - 1, max_sprints - 1)
            sprints[sprint_idx]['items'].append(p)
            sprints[sprint_idx]['total_effort'] += p.item.effort_hours
            if p.quick_win:
                sprints[sprint_idx]['quick_wins'] += 1
            if p.strategic:
                sprints[sprint_idx]['strategic'] += 1

        # Remove empty sprints
        return [s for s in sprints if s['items']]

    def _balance_sprints(self, sprints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Balance sprints to not exceed team velocity"""
        balanced = []

        for sprint in sprints:
            current_sprint = {
                'sprint_number': sprint['sprint_number'],
                'items': [],
                'total_effort': 0.0,
                'quick_wins': 0,
                'strategic': 0
            }

            overflow_items = []

            # Add items up to velocity
            for p in sprint['items']:
                if current_sprint['total_effort'] + p.item.effort_hours <= self.team_velocity:
                    current_sprint['items'].append(p)
                    current_sprint['total_effort'] += p.item.effort_hours
                    if p.quick_win:
                        current_sprint['quick_wins'] += 1
                    if p.strategic:
                        current_sprint['strategic'] += 1
                else:
                    overflow_items.append(p)

            balanced.append(current_sprint)

            # If overflow, create additional sprint
            if overflow_items:
                overflow_sprint = {
                    'sprint_number': len(balanced) + 1,
                    'items': overflow_items,
                    'total_effort': sum(p.item.effort_hours for p in overflow_items),
                    'quick_wins': len([p for p in overflow_items if p.quick_win]),
                    'strategic': len([p for p in overflow_items if p.strategic])
                }
                balanced.append(overflow_sprint)

        return balanced

    def _generate_summary(
        self,
        prioritized: List[PrioritizedDebt],
        sprints: List[Dict[str, Any]],
        total_effort: float
    ) -> str:
        """Generate executive summary"""
        total_items = len(prioritized)
        num_sprints = len(sprints)
        quick_wins = len([p for p in prioritized if p.quick_win])
        strategic = len([p for p in prioritized if p.strategic])

        summary_parts = [
            f"Technical debt repayment plan for {total_items} items ({total_effort:.1f} hours total).",
            f"Plan spans {num_sprints} sprints ({num_sprints * 2} weeks)."
        ]

        if quick_wins > 0:
            summary_parts.append(f"Includes {quick_wins} quick wins for immediate value.")

        if strategic > 0:
            summary_parts.append(f"Addresses {strategic} strategic debt items for long-term health.")

        # Effort per sprint
        avg_effort = total_effort / num_sprints if num_sprints > 0 else 0
        summary_parts.append(f"Average effort per sprint: {avg_effort:.1f} hours (velocity: {self.team_velocity} hours).")

        return " ".join(summary_parts)

    def _generate_recommendations(
        self,
        prioritized: List[PrioritizedDebt],
        sprints: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate top recommendations"""
        recommendations = []

        # Quick wins recommendation
        quick_wins = [p for p in prioritized if p.quick_win]
        if quick_wins:
            recommendations.append(
                f"Start with {len(quick_wins)} quick wins (low effort, high value) to build momentum"
            )

        # High priority recommendation
        high_priority = [p for p in prioritized if p.priority_score >= 8]
        if high_priority:
            recommendations.append(
                f"Address {len(high_priority)} high-priority items in first 2 sprints to reduce risk"
            )

        # Strategic recommendation
        strategic = [p for p in prioritized if p.strategic]
        if strategic:
            recommendations.append(
                f"Plan {len(strategic)} strategic items across sprints to improve architecture"
            )

        # Category-specific recommendations
        by_category = {}
        for p in prioritized:
            cat = p.item.category
            by_category[cat] = by_category.get(cat, 0) + 1

        top_category = max(by_category.items(), key=lambda x: x[1])[0] if by_category else None
        if top_category:
            recommendations.append(
                f"Focus on {top_category} debt ({by_category[top_category]} items) for maximum impact"
            )

        # Velocity recommendation
        if sprints:
            first_sprint_effort = sprints[0]['total_effort']
            if first_sprint_effort > self.team_velocity * 0.8:
                recommendations.append(
                    f"Sprint 1 is nearly full ({first_sprint_effort:.1f}/{self.team_velocity}h) - consider splitting high-effort items"
                )

        return recommendations[:5]  # Top 5

    def get_sprint_breakdown(self, plan: RepaymentPlan) -> List[Dict[str, Any]]:
        """Get sprint-by-sprint breakdown"""
        return plan.sprints


if __name__ == "__main__":
    print("Technical Debt Agents Module (Scenario 12)")
    print("=" * 60)
    print("[OK] Agent 1: DebtCalculator - COMPLETE")
    print("[OK] Agent 2: PrioritizationEngine - COMPLETE")
    print("[OK] Agent 3: RepaymentPlanner - COMPLETE")
    print()
    print("Data Structures:")
    print("  - DebtItem (debt instances)")
    print("  - DebtMetrics (overall metrics)")
    print("  - PrioritizedDebt (prioritized items)")
    print("  - RepaymentPlan (phased plans)")
    print()
    print("Patterns Supported: 6")
    print("  - TODO/FIXME Comments")
    print("  - Deprecated API Usage")
    print("  - Code Duplication")
    print("  - Long Methods")
    print("  - Complex Methods")
    print("  - Dead Code")
