"""Учебные материалы «Академии»: короткие уроки по доступности для преподавателей и методистов.

Структура урока: ``id``, ``wcag``, ``minutes``, тексты ``ru``/``en`` и ``quiz``. Правильные ответы (``answer`` — индекс варианта)
хранятся один раз на вопрос и не отдаются клиенту до отправки ответов. Чтобы добавить урок, допишите словарь в ``LESSONS``;
тест ``test_academy`` проверит, что переводы согласованы.
"""
from __future__ import annotations

LESSONS: list[dict] = [
    {
        "id": "why",
        "wcag": ["1.3.1"],
        "minutes": 5,
        "ru": {
            "title": "Зачем нужна доступность в образовании",
            "summary": "Четыре принципа WCAG (POUR) и кому на самом деле помогает доступный материал.",
            "sections": [
                {"heading": "Не только «особые» студенты", "paragraphs": [
                    "Доступность помогает людям с постоянными нарушениями зрения, слуха, моторики и когнитивными особенностями. Но не только им: у студента может быть сломана рука, он может смотреть лекцию в шумном вагоне, на слабом экране телефона или на неродном языке.",
                    "Во многих странах образовательные организации обязаны обеспечивать равный доступ к материалам. Практичнее думать об этом как о качестве: доступный материал удобнее всем."]},
                {"heading": "Принципы POUR", "points": [
                    "Воспринимаемость: информацию можно увидеть, услышать или прочитать другим способом (альтернативы для изображений, субтитры, контраст).",
                    "Управляемость: всем можно пользоваться с клавиатуры, хватает времени, понятно, где находишься.",
                    "Понятность: текст и интерфейс предсказуемы, ошибки объяснены.",
                    "Надёжность: материал корректно читают скринридеры и другие вспомогательные технологии."]},
            ],
            "example": None,
        },
        "en": {
            "title": "Why accessibility matters in education",
            "summary": "The four WCAG principles (POUR) and who accessible materials really help.",
            "sections": [
                {"heading": "Not only “special” students", "paragraphs": [
                    "Accessibility helps people with permanent visual, hearing, motor and cognitive disabilities. It also helps a student with a broken arm, someone watching a lecture on a noisy train, on a small phone screen, or in a second language.",
                    "In many countries educational institutions must provide equal access to materials. It is more useful to think of accessibility as quality: accessible material is easier for everyone."]},
                {"heading": "The POUR principles", "points": [
                    "Perceivable: information can be seen, heard or read another way (alternatives for images, captions, contrast).",
                    "Operable: everything works with a keyboard, there is enough time, users know where they are.",
                    "Understandable: text and interface are predictable, errors are explained.",
                    "Robust: material works with screen readers and other assistive technologies."]},
            ],
            "example": None,
        },
        "quiz": [
            {"answer": 1,
             "ru": {"q": "Что означает буква P в POUR?", "options": ["Производительность", "Воспринимаемость (Perceivable)", "Приватность"],
                    "explain": "POUR — Perceivable, Operable, Understandable, Robust."},
             "en": {"q": "What does the P in POUR stand for?", "options": ["Performance", "Perceivable", "Privacy"],
                    "explain": "POUR stands for Perceivable, Operable, Understandable, Robust."}},
            {"answer": 2,
             "ru": {"q": "Кому помогают субтитры к лекции?", "options": ["Только глухим студентам", "Только иностранцам", "Глухим, смотрящим без звука, изучающим язык и всем, кому так удобнее"],
                    "explain": "Доступность полезна широкой аудитории, а не только людям с инвалидностью."},
             "en": {"q": "Who benefits from lecture captions?", "options": ["Only deaf students", "Only foreign students", "Deaf students, people watching muted, language learners and anyone who prefers them"],
                    "explain": "Accessibility benefits a wide audience, not only people with disabilities."}},
            {"answer": 0,
             "ru": {"q": "Какой принцип требует, чтобы материалом можно было пользоваться только с клавиатуры?", "options": ["Управляемость", "Понятность", "Надёжность"],
                    "explain": "Работа с клавиатуры — часть принципа управляемости (Operable)."},
             "en": {"q": "Which principle requires that content works with a keyboard alone?", "options": ["Operable", "Understandable", "Robust"],
                    "explain": "Keyboard operation belongs to the Operable principle."}},
        ],
    },
    {
        "id": "images",
        "wcag": ["1.1.1"],
        "minutes": 6,
        "ru": {
            "title": "Описания изображений, схем и формул",
            "summary": "Как писать альтернативный текст, который помогает учиться, а не просто заполняет поле.",
            "sections": [
                {"heading": "Главное правило", "paragraphs": [
                    "Альтернативный текст заменяет изображение для тех, кто его не видит. Спросите себя: что бы я сказал, если бы читал этот материал вслух по телефону?"]},
                {"heading": "Что писать", "points": [
                    "Информативная картинка (график, схема): передайте вывод, а не оформление: «График: с 2019 по 2024 год доля онлайн-курсов выросла с 12 до 41 %».",
                    "Сложная схема или формула: краткое имя в alt и полное описание в тексте рядом или в MathML/LaTeX.",
                    "Декоративная картинка: пустой alt (alt=\"\"), чтобы скринридер её пропустил.",
                    "Не начинайте с «изображение…» или «картинка…» и не повторяйте подпись рядом."]},
            ],
            "example": {"bad": "<img src=\"cell.png\" alt=\"рисунок 3\">", "good": "<img src=\"cell.png\" alt=\"Строение клетки: ядро в центре, вокруг него митохондрии и рибосомы\">", "caption": "Пустое «рисунок 3» ничего не сообщает."},
        },
        "en": {
            "title": "Describing images, diagrams and formulas",
            "summary": "How to write alternative text that helps learning instead of just filling the field.",
            "sections": [
                {"heading": "The main rule", "paragraphs": [
                    "Alternative text replaces the image for people who cannot see it. Ask yourself: what would I say if I read this material aloud over the phone?"]},
                {"heading": "What to write", "points": [
                    "Informative image (chart, diagram): convey the takeaway, not the decoration: “Chart: from 2019 to 2024 the share of online courses grew from 12 to 41%”.",
                    "Complex diagram or formula: short name in alt and the full description nearby, or MathML/LaTeX.",
                    "Decorative image: empty alt (alt=\"\") so screen readers skip it.",
                    "Do not start with “image of…” and do not repeat the visible caption."]},
            ],
            "example": {"bad": "<img src=\"cell.png\" alt=\"figure 3\">", "good": "<img src=\"cell.png\" alt=\"Cell structure: nucleus in the centre surrounded by mitochondria and ribosomes\">", "caption": "“Figure 3” tells the reader nothing."},
        },
        "quiz": [
            {"answer": 2,
             "ru": {"q": "Какой alt у чисто декоративной картинки-разделителя?", "options": ["alt=\"разделитель\"", "alt=\"картинка\"", "alt=\"\" (пустой)"],
                    "explain": "Пустой alt сообщает вспомогательным технологиям, что изображение можно пропустить."},
             "en": {"q": "What alt should a purely decorative divider image have?", "options": ["alt=\"divider\"", "alt=\"image\"", "alt=\"\" (empty)"],
                    "explain": "An empty alt tells assistive technology the image can be skipped."}},
            {"answer": 1,
             "ru": {"q": "Какое описание лучше для графика роста онлайн-курсов?", "options": ["График", "Доля онлайн-курсов выросла с 12 % в 2019 до 41 % в 2024 году", "Рисунок 4"],
                    "explain": "Хорошее описание передаёт вывод, который автор хотел показать графиком."},
             "en": {"q": "Which description fits a chart of online course growth best?", "options": ["Chart", "Share of online courses grew from 12% in 2019 to 41% in 2024", "Figure 4"],
                    "explain": "A good description conveys the point the author wanted the chart to make."}},
            {"answer": 0,
             "ru": {"q": "Как лучше оформить сложную формулу в учебнике на сайте?", "options": ["Разметкой MathML/LaTeX с текстовой записью", "Скриншотом без описания", "Фотографией доски"],
                    "explain": "Текстовая разметка формулы читается скринридером и масштабируется без потери качества."},
             "en": {"q": "How should a complex formula appear in an online textbook?", "options": ["MathML/LaTeX with a text form", "A screenshot with no description", "A photo of a whiteboard"],
                    "explain": "Text markup is read by screen readers and scales without losing quality."}},
        ],
    },
    {
        "id": "structure",
        "wcag": ["1.3.1", "2.4.2", "2.4.6"],
        "minutes": 5,
        "ru": {
            "title": "Заголовки и структура страницы",
            "summary": "Почему заголовок — это не «крупный жирный текст» и как строить навигацию по материалу.",
            "sections": [
                {"heading": "Структура — это навигация", "paragraphs": [
                    "Пользователи скринридеров часто листают страницу по заголовкам, как по оглавлению. Если «заголовки» сделаны только размером шрифта, оглавления у них нет."]},
                {"heading": "Правила", "points": [
                    "На странице один <h1> — название материала.",
                    "Уровни идут по порядку: после h2 следует h3, а не h5.",
                    "Используйте области <main>, <nav>, <header>, <footer> и ссылку «Перейти к содержимому».",
                    "У страницы есть осмысленный <title> и атрибут lang на <html>.",
                    "Списки и таблицы размечайте как списки и таблицы (с <th>), а не пробелами и картинками."]},
            ],
            "example": {"bad": "<p style=\"font-size:24px;font-weight:bold\">Тема 1. Атомы</p>", "good": "<h2>Тема 1. Атомы</h2>", "caption": "Только настоящий заголовок попадёт в оглавление скринридера."},
        },
        "en": {
            "title": "Headings and page structure",
            "summary": "Why a heading is not “big bold text” and how to build navigation through a material.",
            "sections": [
                {"heading": "Structure is navigation", "paragraphs": [
                    "Screen reader users often move through a page by headings, like a table of contents. If “headings” are only a font size, there is no table of contents."]},
                {"heading": "Rules", "points": [
                    "One <h1> per page: the title of the material.",
                    "Levels go in order: an h2 is followed by h3, not h5.",
                    "Use <main>, <nav>, <header>, <footer> and a “Skip to content” link.",
                    "The page has a meaningful <title> and a lang attribute on <html>.",
                    "Mark up lists and tables as lists and tables (with <th>), not with spaces and images."]},
            ],
            "example": {"bad": "<p style=\"font-size:24px;font-weight:bold\">Topic 1. Atoms</p>", "good": "<h2>Topic 1. Atoms</h2>", "caption": "Only a real heading appears in a screen reader's outline."},
        },
        "quiz": [
            {"answer": 1,
             "ru": {"q": "Как сделать заголовок раздела?", "options": ["Увеличить шрифт и сделать жирным", "Использовать тег h2 (или другой уровень заголовка)", "Выделить цветом"],
                    "explain": "Только настоящие заголовки попадают в структуру страницы."},
             "en": {"q": "How do you create a section heading?", "options": ["Increase font size and make it bold", "Use an h2 (or other heading level) element", "Highlight it with color"],
                    "explain": "Only real headings appear in the page structure."}},
            {"answer": 2,
             "ru": {"q": "Какая последовательность уровней заголовков правильная?", "options": ["h1, h4, h2", "h2, h5, h3", "h1, h2, h3, h2"],
                    "explain": "Уровни не должны пропускаться: после h1 идёт h2, после h2 — h3."},
             "en": {"q": "Which heading level sequence is correct?", "options": ["h1, h4, h2", "h2, h5, h3", "h1, h2, h3, h2"],
                    "explain": "Levels must not be skipped: h1 then h2, h2 then h3."}},
            {"answer": 0,
             "ru": {"q": "Зачем нужен атрибут lang на странице?", "options": ["Скринридер выбирает правильное произношение", "Он ускоряет загрузку", "Он включает перевод на все языки"],
                    "explain": "Язык страницы определяет голос и произношение синтезатора речи."},
             "en": {"q": "Why does a page need a lang attribute?", "options": ["A screen reader picks the correct pronunciation", "It speeds up loading", "It enables translation into all languages"],
                    "explain": "The page language selects the speech synthesizer's voice and pronunciation."}},
        ],
    },
    {
        "id": "color",
        "wcag": ["1.4.1", "1.4.3", "1.4.11"],
        "minutes": 5,
        "ru": {
            "title": "Цвет и контраст",
            "summary": "Какой контраст нужен тексту и элементам интерфейса и почему нельзя опираться только на цвет.",
            "sections": [
                {"heading": "Минимальные значения", "points": [
                    "Обычный текст: контраст не ниже 4,5 : 1.",
                    "Крупный текст (от 24 px или от 18,66 px жирным): не ниже 3 : 1.",
                    "Границы полей, значки и состояния элементов: не ниже 3 : 1.",
                    "Уровень AAA для обычного текста: 7 : 1."]},
                {"heading": "Не только цвет", "paragraphs": [
                    "Если правильный и неправильный ответы различаются только красным и зелёным, их не отличат люди с дальтонизмом. Добавьте значок, подпись или узор.",
                    "Ссылки в тексте должны отличаться не только цветом: подчёркивание — самый надёжный способ."]},
                {"heading": "Проверьте себя", "paragraphs": ["Используйте инструмент «Контраст» в этой платформе: он подскажет ближайший допустимый цвет."]},
            ],
            "example": {"bad": "<p style=\"color:#999;background:#fff\">Срок сдачи — пятница</p>", "good": "<p style=\"color:#595959;background:#fff\">Срок сдачи — пятница</p>", "caption": "#999 на белом даёт только 2,8 : 1, а #595959 — 7 : 1."},
        },
        "en": {
            "title": "Color and contrast",
            "summary": "What contrast text and interface elements need and why color alone is not enough.",
            "sections": [
                {"heading": "Minimum values", "points": [
                    "Normal text: contrast of at least 4.5:1.",
                    "Large text (24 px or 18.66 px bold and up): at least 3:1.",
                    "Field borders, icons and control states: at least 3:1.",
                    "Level AAA for normal text: 7:1."]},
                {"heading": "Not color alone", "paragraphs": [
                    "If correct and wrong answers differ only in red and green, people with color blindness cannot tell them apart. Add an icon, a label or a pattern.",
                    "Links inside text should differ by more than color: underlining is the most reliable cue."]},
                {"heading": "Check yourself", "paragraphs": ["Use the Contrast tool in this platform: it suggests the nearest passing color."]},
            ],
            "example": {"bad": "<p style=\"color:#999;background:#fff\">Due on Friday</p>", "good": "<p style=\"color:#595959;background:#fff\">Due on Friday</p>", "caption": "#999 on white gives only 2.8:1, while #595959 gives 7:1."},
        },
        "quiz": [
            {"answer": 1,
             "ru": {"q": "Какой минимальный контраст у обычного текста по WCAG AA?", "options": ["3 : 1", "4,5 : 1", "7 : 1"], "explain": "Для уровня AA обычному тексту нужно 4,5 : 1, крупному — 3 : 1."},
             "en": {"q": "What is the minimum contrast for normal text under WCAG AA?", "options": ["3:1", "4.5:1", "7:1"], "explain": "AA requires 4.5:1 for normal text and 3:1 for large text."}},
            {"answer": 2,
             "ru": {"q": "Как в тесте показать верный ответ доступно?", "options": ["Зелёной рамкой", "Красным текстом для ошибок", "Цветом, значком и подписью «Верно»/«Неверно»"], "explain": "Информация должна дублироваться не цветом: значком или текстом."},
             "en": {"q": "How do you show a correct quiz answer accessibly?", "options": ["With a green border", "With red text for errors", "With color plus an icon and a “Correct”/“Incorrect” label"], "explain": "Information must also be conveyed by something other than color: an icon or text."}},
            {"answer": 0,
             "ru": {"q": "Как надёжнее всего выделить ссылку в тексте?", "options": ["Подчёркиванием", "Только синим цветом", "Курсивом"], "explain": "Подчёркивание заметно независимо от восприятия цвета."},
             "en": {"q": "What is the most reliable way to mark a link in text?", "options": ["Underline", "Blue color only", "Italics"], "explain": "An underline is visible regardless of color perception."}},
        ],
    },
    {
        "id": "media",
        "wcag": ["1.2.1", "1.2.2", "1.2.5"],
        "minutes": 6,
        "ru": {
            "title": "Видео и аудио: субтитры и расшифровки",
            "summary": "Что нужно сделать с лекциями, вебинарами и подкастами, чтобы их мог использовать каждый.",
            "sections": [
                {"heading": "Три слоя доступности", "points": [
                    "Субтитры: речь и важные звуки в синхронизированном тексте. Автосубтитры нужно вычитывать: ошибки в терминах — частая проблема.",
                    "Расшифровка (транскрипт): полный текст для аудио и видео — удобен для поиска, чтения и скринридера.",
                    "Аудиоописание: если важная информация показана только картинкой (схема на доске, эксперимент), её нужно проговорить."]},
                {"heading": "Практика", "points": [
                    "Не включайте автовоспроизведение со звуком.",
                    "Используйте плеер с управлением с клавиатуры.",
                    "Говорите вслух то, что показываете: «на этой схеме слева исходное вещество…»."]},
            ],
            "example": {"bad": "<video src=\"lecture.mp4\" autoplay></video>", "good": "<video src=\"lecture.mp4\" controls>\n  <track kind=\"captions\" src=\"lecture.ru.vtt\" srclang=\"ru\" label=\"Русский\" default>\n</video>", "caption": "Видео с элементами управления и дорожкой субтитров."},
        },
        "en": {
            "title": "Video and audio: captions and transcripts",
            "summary": "What to do with lectures, webinars and podcasts so everyone can use them.",
            "sections": [
                {"heading": "Three layers of access", "points": [
                    "Captions: speech and important sounds as synchronised text. Auto-captions must be proofread: errors in terminology are common.",
                    "Transcript: the full text of audio and video, handy for search, reading and screen readers.",
                    "Audio description: when important information is shown only visually (a diagram on a board, an experiment), say it aloud."]},
                {"heading": "In practice", "points": [
                    "Do not autoplay with sound.",
                    "Use a player operable from the keyboard.",
                    "Say aloud what you show: “on the left of this diagram is the starting compound…”."]},
            ],
            "example": {"bad": "<video src=\"lecture.mp4\" autoplay></video>", "good": "<video src=\"lecture.mp4\" controls>\n  <track kind=\"captions\" src=\"lecture.en.vtt\" srclang=\"en\" label=\"English\" default>\n</video>", "caption": "A video with controls and a captions track."},
        },
        "quiz": [
            {"answer": 0,
             "ru": {"q": "Что нужно сделать с автоматически созданными субтитрами?", "options": ["Вычитать и исправить ошибки", "Ничего: они всегда точные", "Удалить"], "explain": "Распознавание часто искажает термины и имена, их нужно проверять."},
             "en": {"q": "What should you do with auto-generated captions?", "options": ["Proofread and correct errors", "Nothing: they are always accurate", "Delete them"], "explain": "Speech recognition often garbles terms and names; they must be reviewed."}},
            {"answer": 2,
             "ru": {"q": "Что нужно подкасту, чтобы его могли использовать глухие студенты?", "options": ["Более громкий звук", "Фоновая музыка", "Текстовая расшифровка"], "explain": "Для аудио без видео достаточной альтернативой является транскрипт."},
             "en": {"q": "What does a podcast need so deaf students can use it?", "options": ["Louder sound", "Background music", "A text transcript"], "explain": "For audio-only content, a transcript is the needed alternative."}},
            {"answer": 1,
             "ru": {"q": "Как поступить, если на видео схему показывают молча?", "options": ["Ничего не менять", "Проговорить содержание схемы или добавить аудиоописание", "Уменьшить схему"], "explain": "Важная визуальная информация должна быть доступна и на слух."},
             "en": {"q": "What if a video shows a diagram in silence?", "options": ["Change nothing", "Narrate the diagram or add audio description", "Make the diagram smaller"], "explain": "Important visual information must also be available by ear."}},
        ],
    },
    {
        "id": "keyboard",
        "wcag": ["2.1.1", "2.4.7", "2.2.1", "3.3.2"],
        "minutes": 6,
        "ru": {
            "title": "Клавиатура, формы и тесты",
            "summary": "Как сделать так, чтобы страницу и тест можно было пройти без мыши и без спешки.",
            "sections": [
                {"heading": "Клавиатура", "points": [
                    "Все функции доступны клавишами Tab, Shift+Tab, Enter, пробел и стрелки.",
                    "Фокус всегда заметен: не убирайте outline без замены.",
                    "Для кнопок используйте <button>, для ссылок — <a href>. Блок <div onclick> клавиатурой не активируется.",
                    "Всплывающее окно возвращает фокус туда, откуда его открыли, и закрывается клавишей Esc."]},
                {"heading": "Формы и тесты", "points": [
                    "У каждого поля есть связанная подпись <label>; placeholder её не заменяет.",
                    "Ошибки описаны словами и объясняют, как исправить, а не только красной рамкой.",
                    "Для тестов на время предусмотрите продление: людям с моторными или когнитивными особенностями требуется больше времени."]},
            ],
            "example": {"bad": "<div class=\"btn\" onclick=\"send()\">Отправить</div>", "good": "<button type=\"button\" onclick=\"send()\">Отправить</button>", "caption": "Кнопка получает фокус и срабатывает по Enter и пробелу автоматически."},
        },
        "en": {
            "title": "Keyboard, forms and quizzes",
            "summary": "How to make pages and quizzes usable without a mouse and without rushing.",
            "sections": [
                {"heading": "Keyboard", "points": [
                    "Every function works with Tab, Shift+Tab, Enter, Space and arrow keys.",
                    "Focus is always visible: never remove the outline without a replacement.",
                    "Use <button> for buttons and <a href> for links. A <div onclick> cannot be activated from the keyboard.",
                    "A dialog returns focus to where it was opened and closes with Esc."]},
                {"heading": "Forms and quizzes", "points": [
                    "Each field has an associated <label>; a placeholder is not a replacement.",
                    "Errors are described in words and explain how to fix them, not just a red border.",
                    "For timed quizzes provide extensions: people with motor or cognitive disabilities need more time."]},
            ],
            "example": {"bad": "<div class=\"btn\" onclick=\"send()\">Submit</div>", "good": "<button type=\"button\" onclick=\"send()\">Submit</button>", "caption": "A button is focusable and responds to Enter and Space automatically."},
        },
        "quiz": [
            {"answer": 2,
             "ru": {"q": "Какой элемент нужно использовать для кнопки?", "options": ["div с onclick", "span со стилем", "button"], "explain": "Нативная кнопка получает фокус и работает с клавиатуры без доработок."},
             "en": {"q": "Which element should you use for a button?", "options": ["div with onclick", "styled span", "button"], "explain": "A native button is focusable and keyboard-operable out of the box."}},
            {"answer": 1,
             "ru": {"q": "Заменяет ли placeholder подпись поля?", "options": ["Да, если он понятный", "Нет, нужна связанная подпись label", "Да, на мобильных"], "explain": "Placeholder пропадает при вводе и не всегда озвучивается как имя поля."},
             "en": {"q": "Does a placeholder replace a field label?", "options": ["Yes, if it is clear", "No, an associated label is needed", "Yes, on mobile"], "explain": "A placeholder disappears when typing and is not reliably announced as the field name."}},
            {"answer": 0,
             "ru": {"q": "Что важно для теста с таймером?", "options": ["Возможность продлить время", "Таймер покрупнее", "Запрет на паузы"], "explain": "Критерий 2.2.1 требует дать пользователю возможность отключить или продлить ограничение."},
             "en": {"q": "What matters for a quiz with a timer?", "options": ["A way to extend the time", "A bigger timer", "Banning pauses"], "explain": "Criterion 2.2.1 requires letting users turn off or extend time limits."}},
        ],
    },
]

BY_ID = {lesson["id"]: lesson for lesson in LESSONS}
PASS_RATIO = 2 / 3
