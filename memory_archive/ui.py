"""Tkinter kiosk view using the local Robot profile as its demo identity."""
import sqlite3
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from .service import ArchiveError


def build_memory_archive_tab(parent, robot, on_state_change):
    service = robot.memory_archive
    actor_id = robot.profile.user_id
    archives = []
    results = []
    selected_memory = None

    archive_select = ttk.Combobox(parent, state="readonly", width=35)
    archive_select.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
    query = ttk.Entry(parent)
    query.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8)
    result_select = ttk.Combobox(parent, state="readonly")
    result_select.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=6)

    title, event, tags = (ttk.Entry(parent) for _ in range(3))
    for row, label, field in [(3, "제목", title), (4, "발생일 (YYYY-MM-DD / YYYY-MM / YYYY)", event),
                              (5, "태그 (쉼표 구분)", tags)]:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8)
        field.grid(row=row, column=1, columnspan=3, sticky="ew", padx=8, pady=3)
    body = ScrolledText(parent, height=9, wrap="word")
    body.grid(row=6, column=0, columnspan=4, sticky="nsew", padx=8, pady=6)
    visibility = ttk.Combobox(parent, state="readonly", values=("PRIVATE", "FAMILY"), width=12)
    visibility.set("PRIVATE")
    visibility.grid(row=7, column=0, sticky="w", padx=8)
    status = ttk.Label(parent, text="검색어를 비워 두면 선택한 보관함의 기억을 모두 표시합니다.")
    status.grid(row=8, column=0, columnspan=4, sticky="w", padx=8, pady=6)
    parent.columnconfigure(1, weight=1)
    parent.rowconfigure(6, weight=1)

    def invoke(action):
        try:
            action()
        except (ArchiveError, sqlite3.Error) as error:
            message = str(error) if isinstance(error, ArchiveError) else "기억 저장소를 열거나 변경할 수 없습니다."
            messagebox.showerror("가족 기억", message, parent=parent)

    def refresh_archives():
        archives[:] = service.list_archives(actor_id)
        archive_select["values"] = [
            f"{item['name']} ({'가족' if item['family_id'] else '개인'})" for item in archives
        ]
        if archives:
            archive_select.current(0)

    def archive_id():
        index = archive_select.current()
        if index < 0:
            raise ArchiveError("INVALID_INPUT", "보관함을 선택하세요.")
        return archives[index]["archive_id"]

    def search():
        results[:] = service.search(actor_id, query.get(), archive_id=archive_id())
        result_select.set("")
        result_select["values"] = [item["title"] for item in results]
        reset_form()
        status.configure(text=f"검색 결과 {len(results)}건")

    def reset_form():
        nonlocal selected_memory
        selected_memory = None
        for field in (title, event, tags):
            field.delete(0, "end")
        body.delete("1.0", "end")
        visibility.configure(state="readonly")
        visibility.set("PRIVATE")

    def load_memory():
        nonlocal selected_memory
        index = result_select.current()
        if index < 0:
            return
        reset_form()
        selected_memory = service.get_memory(actor_id, results[index]["memory_id"])
        item = selected_memory
        title.insert(0, item["title"])
        precision = {"DAY": 10, "MONTH": 7, "YEAR": 4, "UNKNOWN": 0}[item["date_precision"]]
        event.insert(0, (item["event_start"] or "")[:precision])
        tags.insert(0, ", ".join(item["tags"]))
        body.insert("1.0", item["content"])
        visibility.set(item["visibility"])
        visibility.configure(state="disabled")

    def create_archive(*, family=False):
        dialog_title = "가족 보관함" if family else "개인 보관함"
        name = simpledialog.askstring(dialog_title, "보관함 이름", parent=parent)
        if name is not None:
            if not name.strip():
                raise ArchiveError("INVALID_INPUT", "보관함 이름을 입력하세요.")
            family_id = service.create_family(actor_id, name) if family else None
            new_id = service.create_archive(actor_id, name, family_id=family_id)
            refresh_archives()
            archive_select.current(next(i for i, item in enumerate(archives) if item["archive_id"] == new_id))
            search()

    def save():
        fields = {
            "title": title.get(),
            "content": body.get("1.0", "end-1c"),
            "event_date": event.get().strip(),
            "tags": [part.strip() for part in tags.get().split(",") if part.strip()],
        }
        if selected_memory is None:
            service.create_memory(actor_id, archive_id(), visibility=visibility.get(), **fields)
        else:
            service.update_memory(actor_id, selected_memory["memory_id"], selected_memory["current_version"],
                                  member_ids=selected_memory["member_ids"], **fields)
        search()
        on_state_change()

    def delete():
        if selected_memory and messagebox.askyesno("기억 삭제", "선택한 기억을 삭제할까요?", parent=parent):
            service.delete_memory(actor_id, selected_memory["memory_id"], selected_memory["current_version"])
            search()
            on_state_change()

    def preview():
        answer = service.answer_from_memories(actor_id, query.get())
        sources = "\n".join(f"{row['title']} · {row['revision_id']}" for row in answer["sources"])
        messagebox.showinfo("기억 근거 검색", "\n\n".join(filter(None, (answer["text"], sources))), parent=parent)

    for row, column, label, action in (
        (0, 2, "개인 보관함 만들기", create_archive),
        (0, 3, "새 가족 보관함", lambda: create_archive(family=True)), (1, 2, "보관함 검색", search),
        (1, 3, "근거 미리보기", preview), (7, 1, "새 기억 입력", reset_form),
        (7, 2, "저장", save), (7, 3, "삭제", delete),
    ):
        ttk.Button(parent, text=label, command=lambda callback=action: invoke(callback)).grid(
            row=row, column=column, padx=8, pady=4, sticky="ew"
        )
    result_select.bind("<<ComboboxSelected>>", lambda _: invoke(load_memory))
    archive_select.bind("<<ComboboxSelected>>", lambda _: invoke(search))
    invoke(refresh_archives)
