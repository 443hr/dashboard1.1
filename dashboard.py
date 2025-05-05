import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from azure.storage.blob import BlobServiceClient
from io import BytesIO
import matplotlib.colors as mcolors
import os

# -------------------------------
# Load Azure Blob Storage config from environment variables
# -------------------------------
conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.environ.get("AZURE_BLOB_CONTAINER")
blob_name = "merged_data.xlsx"

if not all([conn_str, container_name, blob_name]):
    st.error("Azure Blob configuration is missing. Please check environment variables.")
    st.stop()

# -------------------------------
# Read Excel file from Azure Blob Storage
# -------------------------------
blob_service_client = BlobServiceClient.from_connection_string(conn_str)
blob_client = blob_service_client.get_container_client(container_name).get_blob_client(blob_name)
stream = blob_client.download_blob().readall()
df = pd.read_excel(BytesIO(stream))

# -------------------------------
# Clean and prepare data
# -------------------------------
df.columns = df.columns.str.strip()
for col in ['Visa Granted', 'Enrollment_status', 'college', 'plan_name']:
    df[col] = df[col].astype(str).str.strip()

df = df[df['college'].str.lower() != 'nan']
df = df[df['college'] != '']

st.title("Visa Grant Status by College")

# -------------------------------
# Mirrored bar chart: Not Enrolled on left, Enrolled on right
# -------------------------------
def plot_mirrored_horizontal(data, title):
    grouped = data.groupby(['plan_name', 'Enrollment_status']).size().unstack(fill_value=0)
    courses = grouped.index.tolist()

    base_colors = list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.XKCD_COLORS.values())
    course_colors = {course: base_colors[i % len(base_colors)] for i, course in enumerate(courses)}

    enrolled_vals = [grouped.loc[c, 'Enrolled'] if 'Enrolled' in grouped.columns else 0 for c in courses]
    not_enrolled_vals = [grouped.loc[c, 'Not Enrolled'] * -1 if 'Not Enrolled' in grouped.columns else 0 for c in courses]

    fig = go.Figure()

    # Not Enrolled: left side
    fig.add_trace(go.Bar(
        y=courses,
        x=not_enrolled_vals,
        name='Not Enrolled',
        orientation='h',
        marker_color=[mcolors.to_rgba(course_colors[c], alpha=0.4) for c in courses],
        hovertemplate='Course: %{y}<br>Not Enrolled: %{customdata}<extra></extra>',
        customdata=[abs(v) for v in not_enrolled_vals]
    ))

    # Enrolled: right side
    fig.add_trace(go.Bar(
        y=courses,
        x=enrolled_vals,
        name='Enrolled',
        orientation='h',
        marker_color=[course_colors[c] for c in courses],
        hovertemplate='Course: %{y}<br>Enrolled: %{x}<extra></extra>'
    ))

    fig.update_layout(
        barmode='relative',
        title=title,
        xaxis=dict(title='Count (← Not Enrolled | Enrolled →)', zeroline=True),
        yaxis=dict(title='Course Name', automargin=True),
        height=40 * len(courses) + 200,
        legend=dict(
            title="Enrollment Status",
            font=dict(size=11)
        ),
        margin=dict(l=150)
    )

    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Loop through colleges and generate plots
# -------------------------------
for college in df['college'].dropna().unique():
    st.header(f"College: {college}")
    college_df = df[df['college'] == college]

    st.subheader("Visa Granted")
    granted_df = college_df[college_df['Visa Granted'].str.upper() == 'YES']
    if not granted_df.empty:
        plot_mirrored_horizontal(granted_df, "Visa Granted by Enrollment Status")
    else:
        st.info("No data available for visa granted.")

    st.subheader("Visa Not Granted")
    not_granted_df = college_df[college_df['Visa Granted'].str.upper() == 'NO']
    if not not_granted_df.empty:
        plot_mirrored_horizontal(not_granted_df, "Visa Not Granted by Enrollment Status")
    else:
        st.info("No data available for visa not granted.")
