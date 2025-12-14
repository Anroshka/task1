# План тестирования

## 1. Цель
Подтвердить выполнение функциональных требований и ключевых user stories; обеспечить регрессионную защиту.

## 2. Уровни тестирования
- **Unit**: модели/валидации/workflow/права.
- **Integration**: сценарии через Django test client (создание дефекта, доступы, экспорт, аналитика).

## 3. Набор проверок (чек‑лист)
- [x] ≥ 5 unit‑тестов (см. tests/test_models_unit.py)
- [x] ≥ 2 интеграционных сценария (см. tests/test_views_integration.py)
- [x] Проверка User Stories по ролям (см. tests/test_permissions_workflow_and_exports.py)
- [ ] Нагрузочное тестирование (см. docs/load-testing.md)

## 4. Команды
- Запуск тестов: `pytest`
