import streamlit as st
from supabase import create_client

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="IPQC Checklist",
    page_icon="📋",
    layout="wide"
)

st.title("📋 IPQC Inspection")


# =========================================================
# SUPABASE CONNECTION
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# GET ACTIVE CHECKLISTS
# =========================================================

master_response = (
    supabase
    .table("checklist_master")
    .select("*")
    .eq("active", True)
    .execute()
)

checklists = master_response.data


if not checklists:
    st.warning("No active checklist found.")
    st.stop()


# =========================================================
# AREA SELECTION
# =========================================================

areas = sorted(list(set(row["area"] for row in checklists)))

area = st.selectbox(
    "Area",
    [""] + areas
)

if not area:
    st.stop()


# =========================================================
# PROCESS SELECTION
# =========================================================

area_checklists = [
    row for row in checklists
    if row["area"] == area
]

processes = sorted(
    list(set(row["process"] for row in area_checklists))
)

process = st.selectbox(
    "Process",
    [""] + processes
)

if not process:
    st.stop()


# =========================================================
# FIND SELECTED CHECKLIST
# =========================================================

selected_checklist = next(
    row for row in area_checklists
    if row["process"] == process
)

checklist_id = selected_checklist["id"]


# =========================================================
# GET ACTIVE REVISION
# =========================================================

version_response = (
    supabase
    .table("checklist_versions")
    .select("*")
    .eq("checklist_id", checklist_id)
    .eq("active", True)
    .execute()
)

versions = version_response.data

if not versions:
    st.error("No active checklist revision found.")
    st.stop()

version = versions[0]

version_id = version["id"]
revision = version["revision"]


# =========================================================
# GET CHECKLIST ITEMS
# =========================================================

items_response = (
    supabase
    .table("checklist_items")
    .select("*")
    .eq("version_id", version_id)
    .eq("active", True)
    .order("sequence")
    .execute()
)

items = items_response.data


# =========================================================
# INSPECTION INFORMATION
# =========================================================

st.divider()

st.subheader(selected_checklist["checklist_name"])

st.caption(
    f"Area: {area}  |  "
    f"Process: {process}  |  "
    f"Revision: {revision}"
)

col1, col2, col3 = st.columns(3)

with col1:
    lot_number = st.text_input("Lot Number")

with col2:
    machine = st.text_input("Machine")

with col3:
    inspector = st.text_input("Inspector")


# =========================================================
# CHECKLIST FORM
# =========================================================

st.divider()

current_section = None

answers = {}

for item in items:

    # -----------------------------------------------------
    # SECTION HEADER
    # -----------------------------------------------------

    if item["section_code"] != current_section:

        current_section = item["section_code"]

        st.markdown(
            f"### {item['section_code']}. "
            f"{item['section_name']}"
        )

    # -----------------------------------------------------
    # ITEM
    # -----------------------------------------------------

    item_id = item["id"]
    item_code = item["item_code"]
    description = item["item_description"]
    input_type = item["input_type"]

    st.markdown(
        f"**{item_code}**  \n"
        f"{description}"
    )


    # -----------------------------------------------------
    # PASS / FAIL / N/A
    # -----------------------------------------------------

    if input_type == "PASS_FAIL_NA":

        answers[item_id] = st.radio(
            "Result",
            ["Pass", "Fail", "N/A"],
            index=None,
            horizontal=True,
            key=f"result_{item_id}",
            label_visibility="collapsed"
        )


    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    elif input_type == "TEXT":

        answers[item_id] = st.text_input(
            description,
            key=f"text_{item_id}",
            label_visibility="collapsed"
        )


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    elif input_type == "DATE":

        answers[item_id] = st.date_input(
            description,
            value=None,
            key=f"date_{item_id}",
            label_visibility="collapsed"
        )

    st.markdown("---")


# =========================================================
# SUBMIT - PROTOTYPE ONLY
# =========================================================

if st.button(
    "Submit Inspection",
    type="primary",
    use_container_width=True
):

    missing = []

    for item in items:

        if item["required"]:

            value = answers.get(item["id"])

            if value is None or value == "":
                missing.append(item["item_code"])

    if missing:

        st.error(
            "Please complete all required items before submission."
        )

        st.write(
            "Missing:",
            ", ".join(missing)
        )

    else:

        st.success(
            "Prototype checklist completed successfully."
        )

        st.write(
            f"{len(items)} checklist inputs completed."
        )
