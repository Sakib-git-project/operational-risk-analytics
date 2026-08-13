const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, PageOrientation, VerticalAlign
} = require("docx");

const data = JSON.parse(fs.readFileSync("register_data.json", "utf8"));

const PAGE_WIDTH = 12240;  // US Letter, portrait, DXA
const MARGIN = 1440;       // 1 inch
const USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN;

const COLOR_HEADER_BG = "1F3864";
const COLOR_ALT_ROW = "F2F2F2";
const COLOR_ACCENT = "1F3864";

function money(v) {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function headerCell(text, widthDXA) {
  return new TableCell({
    width: { size: widthDXA, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, color: "FFFFFF", size: 18 })],
    })],
  });
}

function bodyCell(text, widthDXA, opts = {}) {
  return new TableCell({
    width: { size: widthDXA, type: WidthType.DXA },
    shading: opts.altRow ? { type: ShadingType.CLEAR, fill: COLOR_ALT_ROW } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({ text: String(text), size: 18, bold: !!opts.bold, color: opts.color })],
    })],
  });
}

function buildTable(headers, colWidths, rows) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => headerCell(h, colWidths[i])),
  });
  const bodyRows = rows.map((row, idx) =>
    new TableRow({
      children: row.map((cellVal, i) =>
        bodyCell(cellVal, colWidths[i], { altRow: idx % 2 === 1 })
      ),
    })
  );
  return new Table({
    width: { size: USABLE_WIDTH, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...bodyRows],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 200 },
    children: [new TextRun({ text })],
  });
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160 },
    children: [new TextRun({ text, italics: !!opts.italic, size: 21 })],
  });
}

function riskLevel(likelihood, impact) {
  const score = likelihood * impact;
  if (score >= 16) return { label: "Critical", color: "C00000" };
  if (score >= 9) return { label: "High", color: "E36C09" };
  if (score >= 4) return { label: "Moderate", color: "BF9000" };
  return { label: "Low", color: "548235" };
}

// ---------------------------------------------------------------
// Build document sections
// ---------------------------------------------------------------

const children = [];

// Title block
children.push(
  new Paragraph({
    spacing: { after: 60 },
    children: [new TextRun({ text: "Operational Risk Register", bold: true, size: 44, color: COLOR_ACCENT })],
  }),
  new Paragraph({
    spacing: { after: 40 },
    children: [new TextRun({ text: "Enterprise Operational Risk Management Program", size: 24, color: "595959" })],
  }),
  new Paragraph({
    spacing: { after: 400 },
    children: [new TextRun({ text: `Prepared: ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`, size: 20, color: "808080" })],
  }),
  new Paragraph({
    border: { bottom: { color: COLOR_ACCENT, space: 1, style: BorderStyle.SINGLE, size: 12 } },
    spacing: { after: 300 },
    children: [],
  })
);

// 1. Purpose & Methodology
children.push(sectionHeading("1. Purpose & Methodology"));
children.push(bodyText(
  "This register documents the operational risks identified across the organization, the controls in place to mitigate them, and the quantitative loss modeling used to validate residual risk ratings. It is intended to support risk committee reporting and ongoing governance review."
));
children.push(bodyText(
  "Risks are scored on a 1-5 scale for both likelihood and impact, both before controls (inherent) and after controls (residual). Risk categories follow the Basel II operational risk event-type taxonomy (Internal Fraud, External Fraud, Employment Practices & Workplace Safety, Clients/Products & Business Practices, Damage to Physical Assets, Business Disruption & System Failures, and Execution/Delivery & Process Management)."
));
children.push(bodyText(
  "Residual risk ratings are cross-checked against a Monte Carlo loss simulation built on three years of historical incident data (frequency modeled via Poisson distribution, severity via lognormal distribution, 10,000 simulated years). Risks whose realized losses or simulated tail exposure are inconsistent with their assigned rating are flagged for re-assessment."
));

// 2. Executive Summary / Quantitative Findings
children.push(sectionHeading("2. Quantitative Risk Summary"));
children.push(bodyText(
  "The following figures are derived from the Monte Carlo simulation of historical incident frequency and severity (see accompanying risk_model.py and Power BI dashboard for full methodology and detail)."
));

const m = data.metrics;
const metricsRows = [
  ["Expected Annual Loss", money(m.expected_annual_loss), "Average simulated annual loss across 10,000 scenarios."],
  ["Value at Risk (95%)", money(m.var_95), "Loss threshold not expected to be exceeded in 19 of 20 years."],
  ["Value at Risk (99%)", money(m.var_99), "Loss threshold not expected to be exceeded in 99 of 100 years."],
  ["Conditional VaR (95%)", money(m.cvar_95), "Average loss in the worst 5% of simulated years."],
  ["Unexpected Loss (95%)", money(m.unexpected_loss_95), "Capital buffer needed above expected loss to cover a 1-in-20 bad year."],
];
children.push(buildTable(
  ["Metric", "Value", "Interpretation"],
  [2600, 1800, 5060],
  metricsRows
));
children.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

// 3. Top 10 costliest risks
children.push(sectionHeading("3. Top Risks by Realized Loss"));
children.push(bodyText(
  "Ranking risks by cumulative historical loss (rather than assigned rating alone) surfaces where the register's ratings may need revisiting -- a risk with a moderate rating but high realized loss is a candidate for re-scoring."
));
const topRows = data.top_costliest.map(r => [
  r.risk_id,
  r.category,
  r.unit_name,
  `${r.residual_likelihood} / ${r.residual_impact}`,
  r.incident_count,
  money(r.cumulative_loss),
]);
children.push(buildTable(
  ["ID", "Category", "Business Unit", "Res. L/I", "# Incidents", "Cumulative Loss"],
  [700, 2700, 2400, 1200, 1400, 2060],
  topRows
));
children.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

// 4. Governance gap - overdue control testing
children.push(sectionHeading("4. Governance Gap: Overdue Control Testing"));
children.push(bodyText(
  `${data.overdue_controls.length} controls have not been tested in over 180 days. Controls rated "Weak" and overdue for testing represent the highest-priority governance gap, since their actual effectiveness is unverified. The 10 most overdue are listed below; the full list should be escalated to control owners for re-testing.`
));
const overdueSorted = [...data.overdue_controls].sort((a, b) => b.days_since_tested - a.days_since_tested).slice(0, 10);
const overdueRows = overdueSorted.map(r => [
  r.risk_id,
  r.category,
  r.unit_name,
  r.effectiveness_rating,
  r.last_tested_date,
  r.days_since_tested,
]);
children.push(buildTable(
  ["Risk ID", "Category", "Business Unit", "Effectiveness", "Last Tested", "Days Overdue"],
  [900, 2600, 2400, 1600, 1500, 1460],
  overdueRows
));
children.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

// 5. Full risk register
children.push(sectionHeading("5. Full Risk Register"));
children.push(bodyText(
  "Sorted by residual risk score (likelihood x impact), highest first. All 40 registered risks are listed below."
));
const registerRows = data.risk_register.map(r => {
  const level = riskLevel(r.residual_likelihood, r.residual_impact);
  return [
    r.risk_id,
    r.category,
    r.unit_name,
    `${r.inherent_likelihood} / ${r.inherent_impact}`,
    `${r.residual_likelihood} / ${r.residual_impact}`,
    level.label,
    r.risk_owner,
  ];
});
children.push(buildTable(
  ["ID", "Category", "Business Unit", "Inherent L/I", "Residual L/I", "Residual Level", "Owner"],
  [600, 2500, 2100, 1400, 1400, 1400, 1660],
  registerRows
));

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_WIDTH, height: 15840 },
        margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("Operational_Risk_Register.docx", buffer);
  console.log("Document written.");
});
