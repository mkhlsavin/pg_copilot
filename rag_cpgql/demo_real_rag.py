"""
Демонстрация реальной работы RAG-CPGQL системы
Показывает все этапы обработки: анализ, retrieval, enrichment, generation
"""

import sys
import json
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.workflow.langgraph_workflow import run_workflow

def load_sample_questions(n=10):
    """Загрузка случайных вопросов из датасета"""
    dataset_path = Path("data/all_qa_merged.jsonl")

    print(f"\nЗагрузка вопросов из {dataset_path}...")
    questions = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            qa = json.loads(line.strip())
            questions.append(qa)

    random.seed(42)
    sample = random.sample(questions, n)
    print(f"Выбрано {n} случайных вопросов из {len(questions)} доступных\n")

    return sample

def demo_rag_pipeline():
    """Демонстрация работы RAG pipeline"""

    print("=" * 80)
    print("ДЕМОНСТРАЦИЯ RAG-CPGQL СИСТЕМЫ")
    print("=" * 80)

    # Загрузка вопросов
    questions = load_sample_questions(10)

    results = []
    total_start = time.time()

    for i, qa in enumerate(questions, 1):
        question = qa['question']

        print(f"\n{'-' * 80}")
        print(f"[{i}/10] ВОПРОС:")
        print(f"{question}")
        print(f"\nОригинальные метаданные:")
        print(f"  Темы: {', '.join(qa.get('topics', ['N/A'])[:3])}")
        print(f"  Сложность: {qa.get('difficulty', 'N/A')}")
        print(f"  Источник: {qa.get('source_dataset', 'N/A')}")

        # Запуск workflow
        print(f"\nОбработка через RAG pipeline...")
        start = time.time()
        result = run_workflow(question, verbose=False)
        elapsed = time.time() - start

        # Извлечение состояния
        state = result.get('state', {})

        # Вывод результатов каждого этапа
        print(f"\n✓ РЕЗУЛЬТАТЫ ({elapsed:.2f}s):")

        # 1. Анализ
        print(f"\n  1️⃣ ANALYZER:")
        print(f"     Домен: {state.get('domain', 'N/A')}")
        print(f"     Намерение: {state.get('intent', 'N/A')}")
        print(f"     Сложность: {state.get('complexity', 'N/A')}")
        print(f"     Ключевые слова: {', '.join(state.get('keywords', [])[:5]) if state.get('keywords') else 'N/A'}")

        # 2. Retrieval
        print(f"\n  2️⃣ RETRIEVER:")
        retrieval_meta = state.get('retrieval_metadata', {})
        qa_count = len(state.get('similar_qa', []))
        cpgql_count = len(state.get('cpgql_examples', []))
        print(f"     Q&A найдено: {qa_count} (схожесть: {retrieval_meta.get('avg_qa_similarity', 0):.3f})")
        print(f"     CPGQL примеров: {cpgql_count} (схожесть: {retrieval_meta.get('avg_cpgql_similarity', 0):.3f})")

        # 3. Enrichment
        print(f"\n  3️⃣ ENRICHMENT:")
        enrichment = state.get('enrichment_hints', {})
        coverage = state.get('enrichment_coverage', 0)
        print(f"     Покрытие: {coverage:.1%}")
        print(f"     Тегов сгенерировано: {len(enrichment.get('tags', []))}")
        if enrichment.get('subsystems'):
            print(f"     Подсистемы: {', '.join(enrichment.get('subsystems', [])[:3])}")
        if enrichment.get('function_purposes'):
            print(f"     Назначение функций: {', '.join(enrichment.get('function_purposes', [])[:3])}")

        # 4. Generation
        print(f"\n  4️⃣ GENERATOR:")
        query = state.get('cpgql_query', 'N/A')
        valid = state.get('query_valid', False)
        gen_time = state.get('generation_time', 0)
        print(f"     Валидность: {'✓ VALID' if valid else '✗ INVALID'}")
        print(f"     Время генерации: {gen_time:.2f}s")
        print(f"     Запрос: {query[:100]}{'...' if len(query) > 100 else ''}")

        # Проверка использования тегов
        uses_tags = '.tag.' in query
        uses_nameExact = '.nameExact(' in query
        print(f"     Использует теги: {'✓' if uses_tags else '✗'}")
        print(f"     Использует nameExact: {'✓' if uses_nameExact else '✗'}")

        # 5. Execution (если был)
        exec_success = state.get('execution_success', False)
        if exec_success:
            print(f"\n  5️⃣ EXECUTOR: ✓ Успешно выполнен")
            exec_time = state.get('execution_time', 0)
            print(f"     Время выполнения: {exec_time:.2f}s")
        else:
            print(f"\n  5️⃣ EXECUTOR: ✗ Не выполнен (Joern сервер недоступен)")

        results.append({
            'question': question,
            'result': result,
            'elapsed': elapsed
        })

    # Итоговая статистика
    total_time = time.time() - total_start

    print(f"\n{'=' * 80}")
    print("ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'=' * 80}")

    valid_count = sum(1 for r in results if r['result'].get('valid', False))
    avg_time = sum(r['elapsed'] for r in results) / len(results)

    # Статистика по использованию тегов
    tag_usage = sum(1 for r in results if '.tag.' in r['result'].get('state', {}).get('cpgql_query', ''))

    # Средние метрики
    avg_coverage = sum(r['result'].get('state', {}).get('enrichment_coverage', 0) for r in results) / len(results)

    print(f"\nОбщее:")
    print(f"  Всего вопросов: {len(results)}")
    print(f"  Валидных запросов: {valid_count}/{len(results)} ({valid_count/len(results)*100:.1f}%)")
    print(f"  Среднее время: {avg_time:.2f}s/вопрос")
    print(f"  Общее время: {total_time:.1f}s ({total_time/60:.1f} мин)")

    print(f"\nКачество:")
    print(f"  Использование тегов: {tag_usage}/{len(results)} ({tag_usage/len(results)*100:.1f}%)")
    print(f"  Среднее покрытие enrichment: {avg_coverage:.1%}")

    # Распределение по доменам
    domains = {}
    for r in results:
        domain = r['result'].get('state', {}).get('domain', 'unknown')
        domains[domain] = domains.get(domain, 0) + 1

    print(f"\nРаспределение по доменам:")
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count} вопросов")

    print(f"\n{'=' * 80}")
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print(f"{'=' * 80}\n")

    # Сохранение результатов
    output_file = Path("results/demo_rag_results.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_questions': len(results),
            'total_time': total_time,
            'avg_time_per_question': avg_time,
            'validity_rate': valid_count / len(results),
            'tag_usage_rate': tag_usage / len(results),
            'avg_enrichment_coverage': avg_coverage,
            'results': [{
                'question': r['question'],
                'domain': r['result'].get('state', {}).get('domain'),
                'query': r['result'].get('state', {}).get('cpgql_query'),
                'valid': r['result'].get('valid'),
                'enrichment_coverage': r['result'].get('state', {}).get('enrichment_coverage'),
                'elapsed': r['elapsed']
            } for r in results]
        }, f, indent=2, ensure_ascii=False)

    print(f"Результаты сохранены в: {output_file}\n")

if __name__ == "__main__":
    try:
        demo_rag_pipeline()
    except KeyboardInterrupt:
        print("\n\nДемонстрация прервана пользователем")
    except Exception as e:
        print(f"\n\nОШИБКА: {e}")
        import traceback
        traceback.print_exc()
