from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
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
    Create a line chart for a given metric and save it to a BytesIO stream.
    """
    plt.figure(figsize=(8, 4))
    plt.plot(chart_data['Time'], chart_data[metric_name], marker='o', linestyle='-', color='blue', label=metric_name)
    plt.title(title)
    plt.xlabel('Time')
    plt.ylabel(metric_name)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True)
    plt.legend()

    chart_stream = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_stream, format='png')
    plt.close()

    chart_stream.seek(0)
    return chart_stream

def generate_pdf_report(aggregated_data, management_zone, start_time, metrics, output_filename):
    """
    Generate a PDF report with a title block and embedded line charts.
    """
    pdf = SimpleDocTemplate(output_filename, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading2']
    text_style = styles['Normal']

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

    for dimension, df in aggregated_data.items():
        elements.append(Paragraph(f"<b>{dimension}</b>", style=title_style))
        elements.append(Spacer(1, 24))

        for metric_name in df.columns:
            if metric_name not in ['Dimension', 'Time']:
                chart_stream = create_chart(df, f"{metric_name} Trend for {dimension}", metric_name)
                img = Image(chart_stream, width=500, height=250)
                elements.append(img)
                elements.append(Spacer(1, 24))

        elements.append(Spacer(1, 24))

    pdf.build(elements)
    print(f"PDF report saved to {output_filename}")

def aggregate_data_from_existing_report(file_path):
    """
    Read the existing Excel file and aggregate data for identical Dimensions across tabs.
    """
    df_dict = pd.read_excel(file_path, sheet_name=None)
    aggregated_data = {}

    for sheet_name, df in df_dict.items():
        if 'Dimension' not in df.columns:
            continue
        for dimension in df['Dimension'].unique():
            if dimension not in aggregated_data:
                aggregated_data[dimension] = []
            dimension_data = df[df['Dimension'] == dimension]
            aggregated_data[dimension].append(dimension_data)

    for dimension in aggregated_data:
        aggregated_data[dimension] = pd.concat(aggregated_data[dimension], ignore_index=True)

    return aggregated_data

def main():
    Tk().withdraw()
    print("Please select the existing Dynatrace report file (Excel).")
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not file_path:
        print("No file selected. Exiting...")
        return

    management_zone = input("Enter the Management Zone: ").strip()
    start_time = "now-1w"
    metrics = [
        "Processor", "Memory", "Average Disk Used Percentage",
        "Average Disk Utilzation Time", "Disk Write Time Per Second",
        "Average Disk Queue Length", "Network Adapter In", "Network Adapter Out"
    ]

    print("Aggregating data from the existing report...")
    aggregated_data = aggregate_data_from_existing_report(file_path)

    output_filename = f"{management_zone.replace(':', '').replace(' ', '_')}-Aggregated_Dynatrace_Report-{datetime.now().strftime('%Y%m%d')}.pdf"
    print("Generating the PDF report...")
    generate_pdf_report(aggregated_data, management_zone, start_time, metrics, output_filename)
    print(f"Report saved to {output_filename}")

if __name__ == "__main__":
    main()
