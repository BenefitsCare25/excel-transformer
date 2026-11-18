import React from 'react';
import './Renewal.css';

const Code = ({ children }) => <span className="renewal-code">{children}</span>;

const RenewalAdjGuide = () => (
  <div className="renewal-panel px-4 py-4 space-y-4 text-xs renewal-text">
    <section>
      <h4 className="text-sm font-semibold mb-1">Input files</h4>
      <p className="renewal-muted">
        Two renewal listings in any order. Each needs a sheet named <Code>Employee Listing YYYY</Code>; the
        year decides which file is previous and which is current. Either layout works, and the two files can
        use different layouts:
      </p>
      <ul className="list-disc ml-5 mt-1 space-y-1">
        <li>
          <span className="font-semibold">Classic listing</span>: merged product banners such as{' '}
          <Code>GROUP TERM LIFE (GTL)</Code> above a row of column names, with a{' '}
          <Code>Type of Administration</Code> column per product.
        </li>
        <li>
          <span className="font-semibold">Flat listing</span>: one header row where product columns start with the
          product code, e.g. <Code>GTL EE Eligible Sum Insured</Code>, <Code>GTL Premium</Code>,{' '}
          <Code>GHS Plan/Basis of Cover</Code>, <Code>GHS Premium</Code>.
        </li>
      </ul>
      <p className="renewal-muted mt-1">
        Staff are matched across years by Identification No., then EMP ID, then name and date of birth.
        Premium formulas must have saved results: if a file was produced by another tool, open it in Excel
        and save it before uploading.
      </p>
    </section>

    <section>
      <h4 className="text-sm font-semibold mb-1">Headcount or Named</h4>
      <ul className="list-disc ml-5 space-y-1">
        <li>An Administration Basis column in the listing always wins.</li>
        <li>Medical products (GHS, GMM, GP, SP, GD) with a premium are Headcount.</li>
        <li>
          Life products (GTL, GDD, GPA, GDI) with a premium are Headcount when the sum insured is within the
          FCL and the age next birthday is within the age limit.
        </li>
        <li>
          Over either limit they are Named and excluded from the adjustment, except staff who were already
          Named the previous year (already underwritten), who count as Headcount.
        </li>
        <li>No premium means not covered: no adjustment.</li>
      </ul>
    </section>

    <section>
      <h4 className="text-sm font-semibold mb-1">Output workbook</h4>
      <ul className="list-disc ml-5 space-y-1">
        <li>
          <span className="font-semibold">&lt;Client&gt; Adj</span>: every previous-year row, then every current-year
          row (green), both at last year&apos;s premium: a continuing employee keeps their own, a joiner takes last
          year&apos;s premium for the same cover. Continuing staff net to zero even when the renewal changes the rates.
          Headcount rows adjust by <Code>(current − previous) / 365 × days</Code>; medical adds 9% GST.
        </li>
        <li>
          <span className="font-semibold">Adj Invoice Summary</span>: totals per entity next to a blank Debit/Credit
          Note No. cell, then each employee&apos;s net adjustment per product.
        </li>
        <li>
          <span className="font-semibold">Notes</span>: files, renewal dates, limits used, every Named or over-limit
          decision with its reason, and warnings.
        </li>
      </ul>
    </section>
  </div>
);

export default RenewalAdjGuide;
