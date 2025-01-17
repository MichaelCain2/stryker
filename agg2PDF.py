from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from tkinter import Tk, filedialog

# Define thresholds for green, yellow, red
thresholds = {
    "Processor": {"green": 50, "yellow": 90, "red": 100},
    "Memory": {"green": 30, "yellow": 95, "red": 100},
    "Average Disk Used Percentage": {"green": 60, "yellow": 85, "red": 100},
    "Average Disk Utilzation Time": {"green": 60, "yellow": 85, "red": 100},
    "Disk Write Time Per Second": {"green": 60, "yellow": 900, "red": 1000},
    "Average Disk Queue Length": {"green": 75, "yellow": 200, "red": 500},
    "Network Adapter In": {"green": 500000000, "yellow": 1000000000, "red": 1900000000},
    "Network Adapter Out": {"green": 500000000, "yellow": 2000000000, "red": 2500000000}
}

def create_chart(chart_data, title, metric_name):
    """
    Create a bar chart for a given metric and save it to a BytesIO stream.
    """
    colors = []
    for value in chart_data[metric_name]:
        if value <= thresholds[metric_name]["green"]:
            colors.append("green")
        elif value <= thresholds[metric_name]["yellow"]:
            colors.append("yellow")
        else:
            colors.append("red")

    plt.figure(figsize=(8, 4))
    plt.bar(chart_data['Time'], chart_data[metric_name], color=colors)
    plt.title(title)
    plt.xlabel('Time')
    plt.ylabel(metric_name)
    plt.xticks(rotation=45, ha='right')

    chart_stream = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_stream, format='png')
    plt.close()

    chart_stream.seek(0)
    return chart_stream

def generate_pdf_report(aggregated_data, management_zone, start_time, metrics, output_filename):
    """
    Generate a PDF report with a title block and embedded charts.
    """
    # Initialize the PDF document
    pdf = SimpleDocTemplate(output_filename, pagesize=letter)
    elements = []

    # Get the default style sheet
    styles = getSampleStyleSheet()
    title_style = styles['Heading2']
    text_style = styles['Normal']

    # Generate the title block
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = "Weekly" if "1w" in start_time else "Daily" if "1d" in start_time else "Custom"
    num_servers = len(aggregated_data)
    title_block = [
        Paragraph(f"<b>Team Name/Management Zone:</b> {management_zone}", text_style),
        Paragraph(f"<b>Report Time:</b> {report_time}", text_style),
        Paragraph(f"<b>Report Duration:</b> {start_time}", text_style),
        Paragraph(f"<b>Data Aggregation:</b> {duration}", text_style),
        Paragraph(f"<b>Number of Servers:</b> {num_servers}", text_style),
        Paragraph(f"<b>Resources:</b> {', '.join(metrics)}", text_style),
        Spacer(1, 24)
    ]
    elements.extend(title_block)

    # Iterate through each Dimension (displayName) and its data
    for dimension, df in aggregated_data.items():
        # Add the displayName as the title
        elements.append(Paragraph(f"<b>{dimension}</b>", style=title_style))
        elements.append(Spacer(1, 24))

        # Create and embed charts for each metric
        for metric_name in df.columns:
            if metric_name not in ['Dimension', 'Time']:
                chart_stream = create_chart(df, f"{metric_name} Trend for {dimension}", metric_name)
                img = Image(chart_stream, width=500, height=250)
                elements.append(img)
                elements.append(Spacer(1, 24))

        # Add a page break after each Dimension
        elements.append(Spacer(1, 24))

    # Build the PDF
    pdf.build(elements)
    print(f"PDF report saved to {output_filename}")

def aggregate_data_from_existing_report(file_path):
    """
    Read the existing Excel file and aggregate data for identical Dimensions across tabs.
    """
    df_dict = pd.read_excel(file_path, sheet_name=None)  # Read all tabs into a dictionary
    aggregated_data = {}

    for sheet_name, df in df_dict.items():
        if 'Dimension' not in df.columns:
            continue  # Skip sheets without the Dimension column
        for dimension in df['Dimension'].unique():
            if dimension not in aggregated_data:
                aggregated_data[dimension] = []
            dimension_data = df[df['Dimension'] == dimension]
            aggregated_data[dimension].append(dimension_data)

    for dimension in aggregated_data:
        aggregated_data[dimension] = pd.concat(aggregated_data[dimension], ignore_index=True)

    return aggregated_data

def main():
    # Ask for the location of the first spreadsheet
    Tk().withdraw()
    print("Please select the existing Dynatrace report file (Excel).")
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not file_path:
        print("No file selected. Exiting...")
        return

    # Ask for Management Zone
    management_zone = input("Enter the Management Zone: ").strip()

    # Simulate previously gathered start_time and metrics
    start_time = "Current"  # Adjust based on your context
    metrics = ["Processor", "Memory", "Logical Disks", "Network Adapter"]

    # Aggregate data from the existing report
    print("Aggregating data from the existing report...")
    aggregated_data = aggregate_data_from_existing_report(file_path)

    # Generate a PDF report
    output_filename = f"{management_zone.replace(':', '').replace(' ', '_')}-Aggregated_Dynatrace_Report-{datetime.now().strftime('%Y%m%d')}.pdf"
