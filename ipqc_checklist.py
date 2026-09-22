import streamlit as st
from supabase import create_client
from datetime import datetime
import uuid


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

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


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

areas = sorted(
    list(
        set(
            row["area"]
            for row in checklists
        )
    )
)

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
    row
    for row in checklists
    if row["area"] == area
]

processes = sorted(
    list(
        set(
            row["process"]
            for row in area_checklists
        )
    )
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
    row
    for row in area_checklists
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
    st.error(
        "No active checklist revision found."
    )
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


if not items:
    st.warning(
        "No checklist items found."
    )
    st.stop()


# =========================================================
# INSPECTION INFORMATION
# =========================================================

st.divider()

st.subheader(
    selected_checklist["checklist_name"]
)

st.caption(
    f"Area: {area}  |  "
    f"Process: {process}  |  "
    f"Revision: {revision}"
)


col1, col2, col3 = st.columns(3)


with col1:
    lot_number = st.text_input(
        "Lot Number"
    )


with col2:
    machine = st.text_input(
        "Machine"
    )


with col3:
    inspector = st.text_input(
        "Inspector"
    )


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
    # ITEM INFORMATION
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

        answers[item_id] = {
            "type": "PASS_FAIL_NA",
            "value": st.radio(
                "Result",
                [
                    "Pass",
                    "Fail",
                    "N/A"
                ],
                index=None,
                horizontal=True,
                key=f"result_{item_id}",
                label_visibility="collapsed"
            )
        }


    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    elif input_type == "TEXT":

        answers[item_id] = {
            "type": "TEXT",
            "value": st.text_input(
                description,
                key=f"text_{item_id}",
                label_visibility="collapsed"
            )
        }


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    elif input_type == "DATE":

        answers[item_id] = {
            "type": "DATE",
            "value": st.date_input(
                description,
                value=None,
                key=f"date_{item_id}",
                label_visibility="collapsed"
            )
        }


    st.markdown("---")


# =========================================================
# SUBMIT INSPECTION
# =========================================================

if st.button(
    "Submit Inspection",
    type="primary",
    use_container_width=True
):

    # -----------------------------------------------------
    # VALIDATE HEADER
    # -----------------------------------------------------

    missing_header = []

    if not lot_number.strip():
        missing_header.append(
            "Lot Number"
        )

    if not machine.strip():
        missing_header.append(
            "Machine"
        )

    if not inspector.strip():
        missing_header.append(
            "Inspector"
        )


    # -----------------------------------------------------
    # VALIDATE CHECKLIST
    # -----------------------------------------------------

    missing_items = []


    for item in items:

        if item["required"]:

            answer = answers.get(
                item["id"]
            )

            if not answer:
                missing_items.append(
                    item["item_code"]
                )
                continue

            value = answer["value"]

            if value is None or value == "":
                missing_items.append(
                    item["item_code"]
                )


    # -----------------------------------------------------
    # SHOW VALIDATION ERRORS
    # -----------------------------------------------------

    if missing_header:

        st.error(
            "Please complete the inspection information: "
            + ", ".join(missing_header)
        )


    elif missing_items:

        st.error(
            "Please complete all required checklist items."
        )

        st.write(
            "Missing:",
            ", ".join(missing_items)
        )


    # -----------------------------------------------------
    # SAVE INSPECTION
    # -----------------------------------------------------

    else:

        try:

            # -------------------------------------------------
            # GENERATE UNIQUE INSPECTION NUMBER
            # -------------------------------------------------

            now = datetime.now()

            short_id = (
                uuid.uuid4()
                .hex[:6]
                .upper()
            )

            inspection_no = (
                f"INS-"
                f"{now.strftime('%Y%m%d-%H%M%S')}-"
                f"{short_id}"
            )


            # -------------------------------------------------
            # INSERT INSPECTION HEADER
            # -------------------------------------------------

            header_data = {
                "inspection_no": inspection_no,
                "checklist_id": checklist_id,
                "version_id": version_id,
                "lot_number": lot_number.strip(),
                "machine": machine.strip(),
                "inspector": inspector.strip(),
                "status": "SUBMITTED",
                "submitted_at": now.isoformat()
            }


            header_response = (
                supabase
                .table("inspection_header")
                .insert(header_data)
                .execute()
            )


            if not header_response.data:

                raise Exception(
                    "Inspection header was not created."
                )


            inspection_id = (
                header_response
                .data[0]["id"]
            )


            # -------------------------------------------------
            # PREPARE INSPECTION RESULTS
            # -------------------------------------------------

            result_rows = []


            for item in items:

                item_id = item["id"]

                answer = answers[item_id]

                input_type = answer["type"]

                value = answer["value"]


                result_row = {
                    "inspection_id": inspection_id,
                    "item_id": item_id,
                    "result": None,
                    "text_value": None,
                    "numeric_value": None,
                    "date_value": None,
                    "remark": None
                }


                # ---------------------------------------------
                # PASS / FAIL / N/A
                # ---------------------------------------------

                if input_type == "PASS_FAIL_NA":

                    result_row["result"] = (
                        value
                    )


                # ---------------------------------------------
                # TEXT
                # ---------------------------------------------

                elif input_type == "TEXT":

                    result_row["text_value"] = (
                        value
                    )


                # ---------------------------------------------
                # DATE
                # ---------------------------------------------

                elif input_type == "DATE":

                    result_row["date_value"] = (
                        value.isoformat()
                        if value
                        else None
                    )


                result_rows.append(
                    result_row
                )


            # -------------------------------------------------
            # INSERT ALL RESULTS
            # -------------------------------------------------

            (
                supabase
                .table("inspection_results")
                .insert(result_rows)
                .execute()
            )


            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            st.success(
                "Inspection submitted successfully."
            )

            st.info(
                f"Inspection No: {inspection_no}"
            )

            st.write(
                f"{len(result_rows)} "
                "inspection results saved."
            )


        except Exception as e:

            st.error(
                "Unable to submit inspection."
            )

            st.exception(e)
