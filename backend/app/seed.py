import random
from datetime import datetime, timedelta

from .auth import hash_password
from .db import Base, SessionLocal, engine
from .models import (
    Bookmark,
    Category,
    Comment,
    Event,
    Instruction,
    Rating,
    Reaction,
    Step,
    StepProgress,
    Tag,
    User,
)
from .search import rebuild


def get_category(db, name):
    category = db.query(Category).filter(Category.name == name).first()
    if not category:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def get_tag(db, name):
    tag = db.query(Tag).filter(Tag.name == name).first()
    if not tag:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag


def add_instruction(
    db,
    author,
    title,
    summary,
    category,
    difficulty,
    minutes,
    tags,
    steps,
    status="published",
    verified_by=None,
    forked_from=None,
    created_days_ago=7,
):
    item = Instruction(
        title=title,
        summary=summary,
        category_id=get_category(db, category).id,
        author_id=author.id,
        status=status,
        difficulty=difficulty,
        minutes=minutes,
        forked_from_id=forked_from.id if forked_from else None,
        created_at=datetime.utcnow() - timedelta(days=created_days_ago),
        published_at=(
            datetime.utcnow() - timedelta(days=created_days_ago)
            if status == "published"
            else None
        ),
        verified_at=(
            datetime.utcnow() - timedelta(days=max(created_days_ago - 2, 0))
            if verified_by
            else None
        ),
        verified_by=verified_by.id if verified_by else None,
    )
    db.add(item)
    db.flush()
    for position, (step_title, step_body) in enumerate(steps):
        item.steps.append(
            Step(position=position, title=step_title, body=step_body)
        )
    item.tags = [get_tag(db, tag) for tag in tags]
    db.flush()
    return item


def add_ratings(db, item, scores):
    if item.status != "published":
        return
    keys = [
        f"u:{db.query(User).filter(User.email == 'student@demo.ru').first().id}",
        f"u:{db.query(User).filter(User.email == 'author2@demo.ru').first().id}",
        f"u:{db.query(User).filter(User.email == 'expert@demo.ru').first().id}",
    ]
    keys += [f"s:seed-rating-{item.id}-{index}" for index in range(len(scores))]
    for key, score in zip(keys, scores):
        db.add(Rating(instruction_id=item.id, voter_key=key, score=score))


def add_reactions(db, item, likes, dislikes):
    if item.status != "published":
        return
    for index in range(likes):
        db.add(
            Reaction(
                voter_key=f"s:seed-like-{item.id}-{index}",
                target_type="instruction",
                target_id=item.id,
                value=1,
            )
        )
    for index in range(dislikes):
        db.add(
            Reaction(
                voter_key=f"s:seed-dislike-{item.id}-{index}",
                target_type="instruction",
                target_id=item.id,
                value=-1,
            )
        )
    for step in item.steps[:3]:
        for index in range(random.randint(0, 3)):
            db.add(
                Reaction(
                    voter_key=f"s:seed-step-like-{step.id}-{index}",
                    target_type="step",
                    target_id=step.id,
                    value=1,
                )
            )
        if random.random() < 0.25:
            db.add(
                Reaction(
                    voter_key=f"s:seed-step-dislike-{step.id}",
                    target_type="step",
                    target_id=step.id,
                    value=-1,
                )
            )


def add_events(db, item, runs, probs):
    if item.status != "published":
        return
    probs = (list(probs) + [0.9] * len(item.steps))[: len(item.steps)]
    now = datetime.utcnow()
    for index in range(runs):
        session_id = f"seed-{item.id}-{index}"
        user_id = None
        started = now - timedelta(
            days=random.randint(0, 13),
            minutes=random.randint(0, 1200),
        )
        db.add(
            Event(
                session_id=session_id,
                user_id=user_id,
                instruction_id=item.id,
                type="instruction_start",
                created_at=started,
            )
        )
        moment = started
        finished = True
        for step_index, step in enumerate(item.steps):
            db.add(
                Event(
                    session_id=session_id,
                    user_id=user_id,
                    instruction_id=item.id,
                    step_id=step.id,
                    type="step_view",
                    created_at=moment,
                )
            )
            if random.random() <= probs[step_index]:
                duration = random.randint(15000, 90000)
                db.add(
                    Event(
                        session_id=session_id,
                        user_id=user_id,
                        instruction_id=item.id,
                        step_id=step.id,
                        type="step_complete",
                        duration_ms=duration,
                        created_at=moment + timedelta(milliseconds=duration),
                    )
                )
                moment += timedelta(milliseconds=duration)
            else:
                duration = random.randint(10000, 50000)
                if random.random() < 0.5:
                    db.add(
                        Event(
                            session_id=session_id,
                            user_id=user_id,
                            instruction_id=item.id,
                            step_id=step.id,
                            type="step_skip",
                            duration_ms=duration,
                            created_at=moment + timedelta(milliseconds=duration),
                        )
                    )
                finished = False
                break
        if finished and random.random() < 0.85:
            db.add(
                Event(
                    session_id=session_id,
                    user_id=user_id,
                    instruction_id=item.id,
                    type="instruction_complete",
                    created_at=moment + timedelta(seconds=20),
                )
            )
    item.views = runs + random.randint(20, 120)


def add_student_progress(db, user, item, completed_count, session_id, finished=False):
    for step in item.steps[:completed_count]:
        db.add(
            StepProgress(
                session_id=session_id,
                user_id=user.id,
                instruction_id=item.id,
                step_id=step.id,
                status="completed",
                time_ms=random.randint(20000, 70000),
            )
        )
    if completed_count < len(item.steps):
        db.add(
            StepProgress(
                session_id=session_id,
                user_id=user.id,
                instruction_id=item.id,
                step_id=item.steps[completed_count].id,
                status="viewed",
                time_ms=0,
            )
        )
    moment = datetime.utcnow() - timedelta(days=1)
    db.add(
        Event(
            session_id=session_id,
            user_id=user.id,
            instruction_id=item.id,
            type="instruction_start",
            created_at=moment,
        )
    )
    for step in item.steps[:completed_count]:
        db.add(
            Event(
                session_id=session_id,
                user_id=user.id,
                instruction_id=item.id,
                step_id=step.id,
                type="step_view",
                created_at=moment,
            )
        )
        db.add(
            Event(
                session_id=session_id,
                user_id=user.id,
                instruction_id=item.id,
                step_id=step.id,
                type="step_complete",
                duration_ms=random.randint(20000, 70000),
                created_at=moment + timedelta(seconds=30),
            )
        )
        moment += timedelta(seconds=30)
    if completed_count < len(item.steps):
        db.add(
            Event(
                session_id=session_id,
                user_id=user.id,
                instruction_id=item.id,
                step_id=item.steps[completed_count].id,
                type="step_view",
                created_at=moment,
            )
        )
    if finished:
        db.add(
            Event(
                session_id=session_id,
                user_id=user.id,
                instruction_id=item.id,
                type="instruction_complete",
                created_at=moment + timedelta(seconds=20),
            )
        )


def seed(db):
    if db.query(User).count():
        return False

    random.seed(42)
    student = User(
        email="student@demo.ru",
        password_hash=hash_password("demo123"),
        name="Аня Студентова",
        role="student",
        bio="Второй курс, собираю инструкции для себя и друзей.",
    )
    author = User(
        email="author@demo.ru",
        password_hash=hash_password("demo123"),
        name="Игорь Авторов",
        role="student",
        bio="Пишу гайды по железу и учёбе.",
    )
    expert = User(
        email="expert@demo.ru",
        password_hash=hash_password("demo123"),
        name="Мария Экспертова",
        role="expert",
        bio="Проверяю инструкции на понятность и полноту.",
    )
    author2 = User(
        email="author2@demo.ru",
        password_hash=hash_password("demo123"),
        name="Павел Практиков",
        role="student",
        bio="Люблю короткие чек-листы без воды.",
    )
    db.add_all([student, author, expert, author2])
    db.flush()

    made = {}

    made["pc"] = add_instruction(
        db,
        author,
        "Как собрать ПК",
        "Пошаговая сборка системного блока: от укладки кабелей до первого запуска.",
        "Компьютеры",
        "medium",
        45,
        ["пк", "сборка", "железо"],
        [
            (
                "Подготовьте рабочее место",
                "Освободите стол, уберите ковёр и снимите статику с рук. Наденьте антистатический браслет или периодически касайтесь металлического корпуса.",
            ),
            (
                "Установите блок питания",
                "Закрепите блок питания в корпусе. Если снизу есть решётка для забора воздуха, ставьте вентилятором вниз.",
            ),
            (
                "Установите процессор",
                "Снимите защитную крышку сокета, совместите треугольник на процессоре с меткой на сокете и опустите рычаг до щелчка.",
            ),
            (
                "Установите кулер",
                "Нанесите небольшую каплю термопасты, прикрутите кулер крест-накрест и подключите его к разъёму CPU_FAN.",
            ),
            (
                "Установите оперативную память",
                "Откройте защёлки, вставьте планку до щелчка и начните со второго слота, если их четыре.",
            ),
            (
                "Установите накопитель",
                "Закрепите SSD в M.2 или 2.5-дюймовом отсеке. Для SATA подключите кабель данных и питание.",
            ),
            (
                "Подключите кабели",
                "Подключите 24-pin, 8-pin питания процессора, USB, аудио и кнопки корпуса. Сверяйтесь с инструкцией к материнской плате.",
            ),
            (
                "Проверьте сборку",
                "Включите ПК и зайдите в BIOS. Проверьте температуры, объём памяти и то, что все накопители определились.",
            ),
        ],
        verified_by=expert,
        created_days_ago=18,
    )

    made["certificate"] = add_instruction(
        db,
        author,
        "Как получить справку в деканате",
        "Что подготовить и в каком порядке пройти, чтобы забрать справку с первого раза.",
        "Документы",
        "easy",
        20,
        ["деканат", "справка", "документы"],
        [
            (
                "Уточните, какая справка нужна",
                "Спросите получателя, нужна ли справка о обучении, о стипендии или с места учёбы. От этого зависит форма и срок.",
            ),
            (
                "Подготовьте документы",
                "Возьмите студенческий, паспорт и заявление. Некоторые деканаты просят фотографию или копию приказа.",
            ),
            (
                "Оформите заявление",
                "Заполните заявление в деканате или скачайте бланк с сайта. Укажите, куда и зачем нужна справка.",
            ),
            (
                "Подайте документы",
                "Отдайте пакет документов в деканат и уточните, когда приходить за готовой справкой.",
            ),
            (
                "Заберите справку",
                "Проверьте фамилию, группу и печать. Если нужна справка для банка, сразу уточните, подходит ли форма.",
            ),
        ],
        verified_by=expert,
        created_days_ago=14,
    )

    made["lab"] = add_instruction(
        db,
        author2,
        "Как подготовить отчёт по лабораторной",
        "Чек-лист от методички до подписи преподавателя.",
        "Учёба",
        "medium",
        60,
        ["лабораторная", "отчёт", "учёба"],
        [
            (
                "Изучите методичку",
                "Выпишите требования к оформлению, набору графиков и выводам. Преподаватели часто проверяют именно это.",
            ),
            (
                "Соберите данные",
                "Сохраните измерения, скриншоты и таблицы. Подпишите, к какому опыту относится каждый файл.",
            ),
            (
                "Оформите титульный лист",
                "Проверьте название вуза, кафедры, группы, варианта и ФИО преподавателя.",
            ),
            (
                "Опишите ход работы",
                "Кратко объясните, что делали и какие формулы использовали. Не вставляйте скриншоты без подписей.",
            ),
            (
                "Сделайте выводы",
                "Сравните результат с теорией, укажите погрешность и причины расхождений.",
            ),
            (
                "Проверьте оформление",
                "Сверьте шрифт, отступы, нумерацию и список литературы. Сохраните файл в PDF.",
            ),
        ],
        created_days_ago=12,
    )

    made["docker"] = add_instruction(
        db,
        expert,
        "Как установить Docker",
        "Установка Docker Desktop и первая проверка контейнера за 15 минут.",
        "Софт",
        "easy",
        15,
        ["docker", "софт", "контейнеры"],
        [
            (
                "Проверьте требования",
                "Убедитесь, что на компьютере достаточно места и включена виртуализация. На Windows нужен WSL 2.",
            ),
            (
                "Скачайте установщик",
                "Загрузите Docker Desktop с официального сайта. Не используйте сторонние сборки.",
            ),
            (
                "Установите Docker",
                "Запустите установщик, оставьте стандартные настройки и дождитесь завершения.",
            ),
            (
                "Перезагрузите компьютер",
                "После перезагрузки запустите Docker Desktop и дождитесь, пока значок станет зелёным.",
            ),
            (
                "Проверьте работу",
                "Откройте терминал и выполните docker run hello-world. Если появилось приветствие, всё работает.",
            ),
        ],
        verified_by=expert,
        created_days_ago=10,
    )

    made["dorm"] = add_instruction(
        db,
        author2,
        "Как заселиться в общежитие",
        "Порядок действий и документы для первого заселения.",
        "Быт",
        "easy",
        30,
        ["общежитие", "документы", "быт"],
        [
            (
                "Получите направление",
                "Обратитесь в деканат или студенческий городок и получите направление на заселение.",
            ),
            (
                "Соберите документы",
                "Возьмите паспорт, студенческий, направление, медицинскую справку и фотографии, если их требуют.",
            ),
            (
                "Придите в общежитие",
                "Уточните часы работы коменданта. В выходные заселение может быть только по записи.",
            ),
            (
                "Подпишите договор",
                "Прочитайте правила проживания, размер платы и условия расторжения. Задайте вопросы до подписи.",
            ),
            (
                "Получите ключи",
                "Проверьте, что ключи подходят к комнате и блоку. Запишите номер комнаты и телефон коменданта.",
            ),
            (
                "Осмотрите комнату",
                "Проверьте мебель, розетки и замки. Зафиксируйте повреждения в акте приёма, если они есть.",
            ),
        ],
        created_days_ago=9,
    )

    made["tax"] = add_instruction(
        db,
        expert,
        "Как оформить налоговый вычет",
        "Пошаговая подача документов на социальный или имущественный вычет.",
        "Документы",
        "medium",
        45,
        ["налог", "вычет", "ндфл"],
        [
            (
                "Проверьте право на вычет",
                "Убедитесь, что расходы подходят под вычет и что вы платили НДФЛ. Проверьте сроки.",
            ),
            (
                "Соберите документы",
                "Подготовьте договор, чеки, справку о доходах и документы на объект, если вычет имущественный.",
            ),
            (
                "Заполните декларацию",
                "Заполните 3-НДФЛ в личном кабинете ФНС. Проверьте суммы и коды доходов.",
            ),
            (
                "Подайте документы",
                "Отправьте декларацию и сканы через личный кабинет или отнесите в налоговую.",
            ),
            (
                "Дождитесь проверки",
                "Камеральная проверка обычно занимает до трёх месяцев. Следите за статусом в личном кабинете.",
            ),
            (
                "Получите деньги",
                "После проверки подайте заявление на возврат и укажите реквизиты счёта.",
            ),
        ],
        verified_by=expert,
        created_days_ago=8,
    )

    made["wifi"] = add_instruction(
        db,
        student,
        "Как настроить Wi-Fi в общежитии",
        "Что делать, если сеть есть, а интернет не работает.",
        "Быт",
        "easy",
        10,
        ["wi-fi", "общежитие", "интернет"],
        [
            (
                "Найдите сеть",
                "Подключитесь к сети общежития. Если её нет, уточните название у соседей или коменданта.",
            ),
            (
                "Авторизуйтесь",
                "Откройте страницу входа и введите логин и пароль из договора. Без авторизации интернет не появится.",
            ),
            (
                "Проверьте MAC-адрес",
                "Если вход не работает, проверьте, не включена ли случайная смена MAC-адреса в настройках телефона.",
            ),
            (
                "Обратитесь в поддержку",
                "Позвоните в поддержку и назовите номер комнаты, MAC-адрес и текст ошибки.",
            ),
        ],
        created_days_ago=7,
    )

    made["git"] = add_instruction(
        db,
        expert,
        "Git для новичка",
        "Первый репозиторий, коммит и pull request без паники.",
        "Софт",
        "medium",
        50,
        ["git", "github", "софт"],
        [
            (
                "Установите Git",
                "Скачайте Git с официального сайта и установите со стандартными настройками.",
            ),
            (
                "Настройте имя и почту",
                "Выполните git config --global user.name и user.email. Эти данные попадут в коммиты.",
            ),
            (
                "Создайте репозиторий",
                "Создайте папку проекта и выполните git init. Появится скрытая папка .git.",
            ),
            (
                "Добавьте файлы",
                "Создайте README.md и выполните git add. Проверьте статус через git status.",
            ),
            (
                "Сделайте коммит",
                "Выполните git commit -m с понятным описанием изменений. Коммит фиксирует состояние файлов.",
            ),
            (
                "Создайте ветку",
                "Выполните git checkout -b feature/readme, чтобы не менять основную ветку.",
            ),
            (
                "Отправьте на GitHub",
                "Создайте удалённый репозиторий, добавьте remote и выполните git push.",
            ),
            (
                "Сделайте pull request",
                "Откройте GitHub и создайте pull request из ветки в main. Опишите, что изменилось.",
            ),
        ],
        verified_by=expert,
        created_days_ago=6,
    )

    made["exam"] = add_instruction(
        db,
        author2,
        "Как подготовиться к экзамену",
        "План на неделю, который помогает не зубрить всё в последнюю ночь.",
        "Учёба",
        "easy",
        35,
        ["экзамен", "учёба", "подготовка"],
        [
            (
                "Составьте план",
                "Разбейте темы на дни. Оставьте последний день на повторение и сон, а не на новую теорию.",
            ),
            (
                "Соберите материалы",
                "Скачайте конспекты, вопросы и старые билеты. Отметьте темы, которые знаете хуже всего.",
            ),
            (
                "Пройдите пробный тест",
                "Решите один вариант без подсказок. Так вы поймёте, где теряете время.",
            ),
            (
                "Разберите ошибки",
                "Вернитесь к слабым темам и выпишите короткие шпаргалки своими словами.",
            ),
            (
                "Выспитесь",
                "Перед экзаменом закончите подготовку заранее. Сон влияет на память сильнее ночной зубрёжки.",
            ),
        ],
        created_days_ago=5,
    )

    made["pass"] = add_instruction(
        db,
        author,
        "Как оформить пропуск в кампус",
        "Заявка, фото и получение пропуска без лишних походов.",
        "Документы",
        "easy",
        15,
        ["пропуск", "кампус", "документы"],
        [
            (
                "Заполните заявку",
                "Возьмите бланк в деканате или скачайте с сайта. Укажите цель пропуска и срок действия.",
            ),
            (
                "Приложите фото",
                "Нужна цветная фотография на светлом фоне. Проверьте размер и формат.",
            ),
            (
                "Отправьте в деканат",
                "Передайте заявку и фото сотруднику деканата. Сохраните входящий номер.",
            ),
            (
                "Получите пропуск",
                "Заберите пропуск в указанное время и проверьте, что он открывает нужные двери.",
            ),
        ],
        status="draft",
        created_days_ago=2,
    )

    original = made["pc"]
    fork_steps = [(step.title, step.body) for step in original.steps]
    fork_steps[2] = (
        "Установите процессор по меткам",
        "Посмотрите на маленький треугольник на процессоре и такой же треугольник на сокете. Они должны смотреть друг на друга. Опускайте процессор строго вертикально.",
    )
    fork_steps[3] = (
        "Установите кулер и проверьте крепление",
        "Нанесите пасту размером с горошину. Прикрутите кулер крест-накрест, чтобы не перекосить. Покачайте его: он не должен двигаться.",
    )
    made["pc_fork"] = add_instruction(
        db,
        author2,
        "Как собрать ПК",
        "Улучшенная версия сборки: больше фото-подсказок на самых сложных шагах.",
        "Компьютеры",
        "medium",
        45,
        ["пк", "сборка", "железо"],
        fork_steps,
        forked_from=original,
        created_days_ago=4,
    )

    add_ratings(db, made["pc"], [5, 5, 5, 4, 5, 4, 5, 5, 4, 5])
    add_ratings(db, made["certificate"], [5, 4, 5, 5, 4, 5, 4])
    add_ratings(db, made["lab"], [4, 4, 5, 3, 4, 4, 5])
    add_ratings(db, made["docker"], [5, 5, 5, 5, 4, 5, 5])
    add_ratings(db, made["dorm"], [4, 4, 5, 4, 3, 4])
    add_ratings(db, made["tax"], [5, 4, 4, 5, 4, 5, 4])
    add_ratings(db, made["wifi"], [4, 4, 3, 4, 5])
    add_ratings(db, made["git"], [5, 5, 4, 5, 5, 4, 5, 5])
    add_ratings(db, made["exam"], [4, 5, 4, 4, 5, 4])
    add_ratings(db, made["pc_fork"], [5, 5, 5, 5, 4, 5, 5, 5])

    add_reactions(db, made["pc"], 14, 1)
    add_reactions(db, made["certificate"], 9, 0)
    add_reactions(db, made["lab"], 7, 1)
    add_reactions(db, made["docker"], 12, 0)
    add_reactions(db, made["dorm"], 6, 1)
    add_reactions(db, made["tax"], 8, 1)
    add_reactions(db, made["wifi"], 4, 2)
    add_reactions(db, made["git"], 11, 0)
    add_reactions(db, made["exam"], 5, 1)
    add_reactions(db, made["pc_fork"], 7, 0)

    add_events(db, made["pc"], 70, [0.95, 0.92, 0.55, 0.82, 0.9, 0.88, 0.9, 0.92])
    add_events(db, made["certificate"], 40, [0.95, 0.7, 0.85, 0.9, 0.95])
    add_events(db, made["lab"], 35, [0.95, 0.9, 0.65, 0.85, 0.9, 0.9])
    add_events(db, made["docker"], 50, [0.97, 0.9, 0.8, 0.95, 0.95])
    add_events(db, made["dorm"], 30, [0.95, 0.85, 0.8, 0.6, 0.9, 0.9])
    add_events(db, made["tax"], 35, [0.95, 0.85, 0.6, 0.85, 0.9, 0.9, 0.9])
    add_events(db, made["wifi"], 25, [0.95, 0.6, 0.8, 0.9])
    add_events(db, made["git"], 45, [0.97, 0.95, 0.9, 0.85, 0.7, 0.85, 0.9, 0.9])
    add_events(db, made["exam"], 25, [0.95, 0.85, 0.7, 0.85, 0.9])
    add_events(db, made["pc_fork"], 30, [0.97, 0.95, 0.85, 0.9, 0.95, 0.92, 0.92, 0.95])

    add_student_progress(db, student, made["pc"], 3, "demo-student")
    add_student_progress(
        db,
        student,
        made["git"],
        len(made["git"].steps),
        "demo-student-git",
        finished=True,
    )

    db.add(
        Comment(
            instruction_id=made["pc"].id,
            step_id=made["pc"].steps[2].id,
            user_id=student.id,
            kind="suggestion",
            body="Добавьте фото сокета и метки на процессоре: на схемах они выглядят иначе.",
        )
    )
    parent = Comment(
        instruction_id=made["pc"].id,
        user_id=author2.id,
        kind="comment",
        body="Собрал по этой инструкции, всё завелось. Не хватило только фото кабелей корпуса.",
    )
    db.add(parent)
    db.flush()
    db.add(
        Comment(
            instruction_id=made["pc"].id,
            user_id=author.id,
            parent_id=parent.id,
            kind="comment",
            body="Спасибо, добавлю фото кабелей в следующую версию.",
        )
    )
    db.add(
        Comment(
            instruction_id=made["certificate"].id,
            step_id=made["certificate"].steps[1].id,
            user_id=student.id,
            kind="suggestion",
            body="Напишите, что справку можно заказать через личный кабинет, если не нужно физическое заверение.",
        )
    )
    db.add(
        Comment(
            instruction_id=made["lab"].id,
            step_id=made["lab"].steps[4].id,
            user_id=student.id,
            kind="comment",
            body="Преподаватель требует подпись руководителя на выводах.",
        )
    )
    db.add(
        Comment(
            instruction_id=made["docker"].id,
            step_id=made["docker"].steps[1].id,
            user_id=author2.id,
            kind="comment",
            body="На Linux Docker Desktop не нужен, там просто Docker Engine.",
        )
    )
    db.add(
        Comment(
            instruction_id=made["dorm"].id,
            step_id=made["dorm"].steps[3].id,
            user_id=expert.id,
            kind="suggestion",
            body="Добавьте ссылку на образец договора и часы работы коменданта.",
        )
    )
    db.add(
        Comment(
            instruction_id=made["pc_fork"].id,
            step_id=made["pc_fork"].steps[2].id,
            user_id=student.id,
            kind="comment",
            body="Вот с фото метки стало понятно, спасибо.",
        )
    )
    db.add(
        Comment(
            instruction_id=made["tax"].id,
            step_id=made["tax"].steps[2].id,
            user_id=student.id,
            kind="suggestion",
            body="Где взять справку о доходах, если работодатель не выдаёт её на руки?",
        )
    )
    resolved = Comment(
        instruction_id=made["git"].id,
        step_id=made["git"].steps[4].id,
        user_id=student.id,
        kind="comment",
        body="После git commit не забудьте git push, иначе на GitHub ничего не будет.",
        resolved=True,
    )
    db.add(resolved)
    db.add(
        Comment(
            instruction_id=made["exam"].id,
            step_id=made["exam"].steps[2].id,
            user_id=author.id,
            kind="comment",
            body="Пробный тест лучше делать за неделю, а не за день.",
        )
    )

    db.add(Bookmark(user_id=student.id, instruction_id=made["pc"].id))
    db.add(Bookmark(user_id=student.id, instruction_id=made["docker"].id))
    db.add(Bookmark(user_id=student.id, instruction_id=made["git"].id))
    db.add(Bookmark(user_id=author.id, instruction_id=made["certificate"].id))

    db.commit()
    rebuild(db)
    return True


if __name__ == "__main__":
    import sys

    if "--reset" in sys.argv:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    else:
        Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        created = seed(session)
        print("seed:", "created" if created else "skipped")
    finally:
        session.close()
