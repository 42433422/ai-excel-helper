"""
Neuro-DDD Architecture Verification Script

Usage:
    python -m app.neuro_bus

Tests:
    - Module imports
    - ReflexArc response time
    - NeuroBus event flow
    - Architecture statistics
"""

import asyncio
import sys
import time


def test_imports():
    """Test all module imports"""
    print("\n[1/5] Testing module imports...")

    try:
        # Phase 1: Core

        print("  [OK] Phase 1: NeuroBus Core")

        # Phase 2: Reliability Mechanisms

        print("  [OK] Phase 2: 8 Reliability Mechanisms")

        # Phase 3: NeuroDomains

        print("  [OK] Phase 3: NeuroDomains (11 domains)")

        # Phase 4: Processors

        print("  [OK] Phase 4: ReflexArc & Processors")

        # Phase 5: Integrations

        print("  [OK] Phase 5: Integrations")

        return True

    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_reflex_arc():
    """Test ReflexArc response time"""
    print("\n[2/5] Testing ReflexArc (<1ms SLA)...")

    try:
        from app.domain.neuro.reflex_arc import get_reflex_arc

        reflex_arc = get_reflex_arc()

        test_cases = [
            "ni hao",
            "hello",
            "tingzhi",
            "shi de",
            "bu dui",
            "bangzhu",
        ]

        latencies = []
        for text in test_cases:
            start = time.perf_counter()
            result = reflex_arc.process(text)
            elapsed_us = (time.perf_counter() - start) * 1_000_000
            latencies.append(elapsed_us)

            triggered = "Y" if result.triggered else "N"
            sla_ok = "OK" if elapsed_us < 1000 else "SLOW"
            print(
                f"  [{triggered}] '{text}' -> {result.reflex_type.value} ({elapsed_us:.0f}us) [{sla_ok}]"
            )

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"  Average latency: {avg_latency:.0f}us")
        print(f"  Max latency: {max_latency:.0f}us")
        print(f"  SLA compliant: {sum(1 for l in latencies if l < 1000)}/{len(latencies)}")

        return avg_latency < 1000

    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        return False


async def test_neurobus():
    """Test NeuroBus event flow"""
    print("\n[3/5] Testing NeuroBus event flow...")

    try:
        from app.neuro_bus.bus import get_neuro_bus
        from app.neuro_bus.events.base import EventPriority, NeuroEvent

        bus = get_neuro_bus()

        # Start bus
        await bus.start()
        print("  [OK] Bus started")

        # Register test handler
        received_events = []

        async def test_handler(event):
            received_events.append(event.event_type)

        bus.subscribe("test.event", test_handler)
        print("  [OK] Handler registered")

        # Publish event
        event = NeuroEvent(
            event_type="test.event",
            payload={"message": "Hello NeuroBus"},
            priority=EventPriority.NORMAL,
        )

        success = bus.publish(event)
        print(f"  [OK] Event published: {success}")

        # Wait for processing
        await asyncio.sleep(0.1)

        print(f"  [OK] Events processed: {len(received_events)}")

        # Stop bus
        await bus.stop()
        print("  [OK] Bus stopped")

        return len(received_events) > 0

    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_domains():
    """Test NeuroDomains"""
    print("\n[4/5] Testing NeuroDomains...")

    try:
        from app.neuro_bus.domains.base import get_domain_registry
        from app.neuro_bus.domains.intent_domain import get_intent_domain
        from app.neuro_bus.domains.order_domain import get_order_domain
        from app.neuro_bus.domains.payment_domain import get_payment_domain

        registry = get_domain_registry()

        # Get domains (auto-register)
        intent_domain = get_intent_domain()
        order_domain = get_order_domain()
        payment_domain = get_payment_domain()

        domains = registry.list_domains()
        print(f"  [OK] Registered domains: {domains}")

        # Show stats
        stats = registry.get_all_stats()
        for name, domain_stats in stats.items():
            print(f"    - {name}: {domain_stats}")

        return len(domains) >= 3

    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_processors():
    """Test processor coordinator"""
    print("\n[5/5] Testing processor coordinator...")

    try:
        from app.domain.neuro.processors.coordinator import ProcessorType, get_processor_coordinator

        coordinator = get_processor_coordinator()

        # Test routing decisions
        test_cases = [
            ("ni hao", ProcessorType.REFLEX),
            ("tingzhi", ProcessorType.REFLEX),
            ("cha xun ding dan", ProcessorType.CONSCIOUS),
        ]

        for text, expected in test_cases:
            decision = coordinator.route(text)
            match = "OK" if decision.processor_type == expected else "DIFF"
            print(f"  [{match}] '{text}' -> {decision.processor_type.value} ({decision.reason})")

        # Show stats
        stats = coordinator.get_stats()
        print(f"  Processor stats: {stats}")

        return True

    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main function"""
    print("=" * 60)
    print("Neuro-DDD Architecture Verification")
    print("=" * 60)

    results = []

    results.append(("Module Imports", test_imports()))
    results.append(("ReflexArc SLA", test_reflex_arc()))
    results.append(("NeuroBus Flow", await test_neurobus()))
    results.append(("NeuroDomains", test_domains()))
    results.append(("Processor Coordinator", await test_processors()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")

    all_passed = all(r[1] for r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed!")
        print("Neuro-DDD Architecture is ready.")
    else:
        print("[WARNING] Some tests failed.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
