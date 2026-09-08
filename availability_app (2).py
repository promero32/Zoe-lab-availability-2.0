import streamlit as st
import pandas as pd
from numbers_parser import Document

st.set_page_config(page_title="Open Lab Availability", layout="wide", page_icon="📅")

# ── Load & parse data ──────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    # UPDATE THIS PATH to where your .numbers file is saved on your computer
    doc = Document("Open Lab Availability.numbers")
    sheet = doc.sheets[0]
    table = sheet.tables[0]
    rows = list(table.iter_rows())
    data = [[str(cell.value) if cell.value is not None else "" for cell in row] for row in rows]
    df = pd.DataFrame(data[1:], columns=data[0])
    df.rename(columns={"Date / Time": "datetime"}, inplace=True)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime"])
    df["date"] = df["datetime"].dt.date
    df["time"] = df["datetime"].dt.strftime("%I:%M %p")
    df = df[df["datetime"].dt.minute.isin([0, 30])].copy()
    df.reset_index(drop=True, inplace=True)
    df.columns = [c.strip() for c in df.columns]
    return df

df = load_data()
all_names = sorted([c for c in df.columns if c not in ("datetime", "date", "time")])
all_dates = sorted(df["date"].unique())

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("🔍 Filters")

selected_date = st.sidebar.selectbox(
    "Select Date",
    all_dates,
    format_func=lambda d: d.strftime("%A, %b %d")
)

selected_names = st.sidebar.multiselect(
    "Filter by Person(s)",
    all_names,
    default=[],
    placeholder="Show all"
)

show_only_available = st.sidebar.checkbox("Only show time slots with availability", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📩 Schedule a Meeting")

meeting_requester = st.sidebar.text_input("Your name")
meeting_time = st.sidebar.selectbox(
    "Proposed time",
    df[df["date"] == selected_date]["time"].tolist()
)
meeting_notes = st.sidebar.text_area("Notes (optional)", height=80)

if st.sidebar.button("✅ Submit Request", use_container_width=True):
    if meeting_requester.strip():
        st.sidebar.success(f"Request submitted!\n\n**{meeting_requester}** → {selected_date.strftime('%b %d')} at {meeting_time}")
    else:
        st.sidebar.warning("Please enter your name.")

# ── Main area ──────────────────────────────────────────────────────────────────
st.title("📅 Open Lab Availability")
st.caption(f"Showing availability for **{selected_date.strftime('%A, %B %d, %Y')}**")

day_df = df[df["date"] == selected_date].copy()
names_to_show = selected_names if selected_names else all_names

# ── Summary row ───────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
available_count = sum(
    1 for n in names_to_show
    if (day_df[n].isin(["Available", "If needed"])).any()
)
col1.metric("People Available", available_count, f"out of {len(names_to_show)}")
col2.metric("Time Slots", len(day_df))
col3.metric("Date", selected_date.strftime("%b %d"))

st.markdown("---")

# ── Availability grid ──────────────────────────────────────────────────────────
st.subheader("🗓️ Availability Grid")

def color_cell(val):
    if val == "Available":
        return "background-color: #22c55e; color: white; font-weight: bold; text-align: center;"
    elif val == "If needed":
        return "background-color: #f59e0b; color: white; font-weight: bold; text-align: center;"
    else:
        return "background-color: #f1f5f9; color: #cbd5e1; text-align: center;"

grid = day_df[["time"] + names_to_show].copy()

if show_only_available:
    has_avail = grid[names_to_show].isin(["Available", "If needed"]).any(axis=1)
    grid = grid[has_avail]

grid = grid.set_index("time")
grid_display = grid.replace("", "–")
styled = grid_display.style.map(color_cell)
st.dataframe(styled, use_container_width=True, height=min(600, 38 + 35 * len(grid)))

st.markdown(
    """
    <div style='display:flex; gap:16px; margin-top:8px; font-size:0.85rem;'>
        <span style='background:#22c55e;color:white;padding:3px 10px;border-radius:4px;'>Available</span>
        <span style='background:#f59e0b;color:white;padding:3px 10px;border-radius:4px;'>If needed</span>
        <span style='background:#f1f5f9;color:#94a3b8;padding:3px 10px;border-radius:4px;border:1px solid #e2e8f0;'>– Not available</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ── Best meeting times ─────────────────────────────────────────────────────────
st.subheader("🏆 Best Times to Meet")
st.caption("Ranked by number of people available")

day_df2 = day_df[["time"] + names_to_show].copy()
day_df2["Available Count"] = day_df2[names_to_show].isin(["Available"]).sum(axis=1)
day_df2["If Needed Count"] = day_df2[names_to_show].isin(["If needed"]).sum(axis=1)
day_df2["Total"] = day_df2["Available Count"] + day_df2["If Needed Count"]
best = day_df2[["time", "Available Count", "If Needed Count", "Total"]].sort_values("Total", ascending=False).head(10)
best.columns = ["Time", "Available ✅", "If Needed 🟡", "Total 👥"]
st.dataframe(best.reset_index(drop=True), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Export ─────────────────────────────────────────────────────────────────────
st.subheader("⬇️ Export Availability")

col_a, col_b = st.columns(2)

with col_a:
    export_df = day_df[["time"] + names_to_show].copy()
    csv_bytes = export_df.to_csv(index=False).encode()
    st.download_button(
        "📄 Download CSV (current date)",
        data=csv_bytes,
        file_name=f"availability_{selected_date}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_b:
    full_export = df[["date", "time"] + names_to_show].copy()
    full_csv = full_export.to_csv(index=False).encode()
    st.download_button(
        "📦 Download CSV (all dates)",
        data=full_csv,
        file_name="availability_all.csv",
        mime="text/csv",
        use_container_width=True
    )
