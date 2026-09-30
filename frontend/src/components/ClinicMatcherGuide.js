import React from 'react';

export const ClinicUploadHelp = ({ fileType }) => (
  <details className="mb-3 text-sm text-gray-700">
    <summary className="w-fit cursor-pointer rounded text-blue-700 underline underline-offset-4 hover:text-blue-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600">
      {fileType === 'base' ? 'What goes in the base file?' : 'What goes in the comparison file?'}
    </summary>
    <div className="mt-2 space-y-2 max-w-prose">
      <p>
        Both files must be Excel (.xlsx or .xls) with a <strong>Clinic Name</strong> column.
        Their layouts and extra columns can differ. Put headers in the first row and remove subtotals and section headings.
      </p>
      {fileType === 'base' ? (
        <p>
          Use your panel master list to check which claimed clinics are on the panel.
          To analyse Top 10/20 clinics or generate a utilisation report, put claims data here instead;
          those features use the base file only.
        </p>
      ) : (
        <p>
          Use a clinic list or a cleaned claims summary. Rename pivot-table <strong>Row Labels</strong> to <strong>Clinic Name</strong>.
          Claimant counts, visits and amounts in this file are not included in the match report.
        </p>
      )}
      <p>Postal Code and Unit Number are optional, but help match clinics with different names. See the guide above for examples.</p>
    </div>
  </details>
);

const ClinicMatcherGuide = () => (
  <details className="mt-4 border-t border-gray-200 pt-4 text-gray-700">
    <summary className="w-fit cursor-pointer rounded font-semibold text-blue-700 underline underline-offset-4 hover:text-blue-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600">
      How to use Clinic Matcher & required columns
    </summary>
    <div className="mt-5 space-y-6 text-sm leading-relaxed">
      <section aria-labelledby="clinic-guide-files">
        <h3 id="clinic-guide-files" className="text-base font-semibold text-gray-900">Choose which file goes where</h3>
        <p className="mt-2 max-w-prose">Both uploads must be Excel (.xlsx or .xls). They do not need the same layout, column order or extra columns.</p>
        <dl className="mt-3 space-y-3 max-w-prose">
          <div>
            <dt className="font-semibold text-gray-900">Check claims against the AIA-FHG panel</dt>
            <dd>Base: AIA-FHG panel master list. Comparison: claims clinic list or cleaned claims pivot table.</dd>
          </div>
          <div>
            <dt className="font-semibold text-gray-900">Analyse the most visited clinics or find panel alternatives</dt>
            <dd>Base: claims data with visit counts, or individual claim rows. Comparison: panel master list. Top 10/20 analysis, utilisation and nearest alternatives start from the base file.</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="clinic-guide-columns">
        <h3 id="clinic-guide-columns" className="text-base font-semibold text-gray-900">Prepare your columns</h3>
        <p className="mt-2 max-w-prose">Use these header names for reliable detection. Put headers in the first row of every relevant sheet; all sheets are read. For a clinic list or summary, keep one row per clinic branch.</p>
        <p className="mt-2 text-gray-600 md:hidden">Scroll the table sideways to read all column details.</p>
        <div role="region" aria-label="Scrollable column requirements" tabIndex={0} className="mt-3 overflow-x-auto rounded-lg border border-gray-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
          <table className="w-full min-w-[640px] text-left">
            <caption className="sr-only">Clinic Matcher column requirements for the base and comparison files</caption>
            <thead className="bg-gray-50 text-gray-900">
              <tr>
                <th scope="col" className="px-4 py-3 font-semibold">Column header</th>
                <th scope="col" className="px-4 py-3 font-semibold">When needed</th>
                <th scope="col" className="px-4 py-3 font-semibold">What to enter</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr>
                <th scope="row" className="px-4 py-3 font-semibold text-gray-900">Clinic Name</th>
                <td className="px-4 py-3">Required in both files</td>
                <td className="px-4 py-3">Clinic name including the branch, where applicable. Blank names are skipped.</td>
              </tr>
              <tr>
                <th scope="row" className="px-4 py-3 font-semibold text-gray-900">Postal Code / Unit Number</th>
                <td className="px-4 py-3">Optional in both files</td>
                <td className="px-4 py-3">Six-digit Singapore postal code (keep leading zeros) and unit, e.g. #01-23. Supply both to match by location.</td>
              </tr>
              <tr>
                <th scope="row" className="px-4 py-3 font-semibold text-gray-900">BLK / Road Name / Building Name / Address</th>
                <td className="px-4 py-3">Optional in both files</td>
                <td className="px-4 py-3">Separate address fields, or one Address column. Dedicated Postal Code and Unit Number columns are more reliable for location matching.</td>
              </tr>
              <tr>
                <th scope="row" className="px-4 py-3 font-semibold text-gray-900">Visit Count</th>
                <td className="px-4 py-3">Base summary for Top 10/20</td>
                <td className="px-4 py-3">Numeric whole-number visits per clinic. Visits and Unique Visit Count are also recognised. More than 50% of detected clinics must have a positive count to enable Top 10/20.</td>
              </tr>
              <tr>
                <th scope="row" className="px-4 py-3 font-semibold text-gray-900">PAID AMT.</th>
                <td className="px-4 py-3">Base claims data for utilisation</td>
                <td className="px-4 py-3">Numeric paid amount per claim, without currency text. Paid Amount and Total Paid are also recognised for utilisation. Use individual claim rows for this report.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="clinic-guide-pivot" className="max-w-prose">
        <h3 id="clinic-guide-pivot" className="text-base font-semibold text-gray-900">Using a claims pivot table</h3>
        <ol className="mt-2 list-decimal pl-5 space-y-2">
          <li>Copy the summary into a clean sheet, preferably as values, with headers in row 1.</li>
          <li>Rename <strong>Row Labels</strong> to <strong>Clinic Name</strong>.</li>
          <li>Remove category headings such as <strong>Panel GP</strong>, subtotals and <strong>Grand Total</strong>. Otherwise they can be treated as clinic names.</li>
          <li>For Top 10/20 analysis, rename <strong>Distinct Count of Visit S/No.</strong> to <strong>Visit Count</strong> and upload the summary as the base file.</li>
        </ol>
        <p className="mt-3">You may keep claimant counts and claim amounts as extra columns for your own reference. They are not used for clinic matching or carried over from the comparison file into the exported report.</p>
        <p className="mt-2">A pivot summary works for clinic matching and Top 10/20 visit ranking. The utilisation report counts claim rows per clinic; uploading a summary would count one row as one visit. Use individual claim rows for accurate utilisation.</p>
      </section>

      <section aria-labelledby="clinic-guide-matching" className="max-w-prose">
        <h3 id="clinic-guide-matching" className="text-base font-semibold text-gray-900">How clinics are matched</h3>
        <p className="mt-2">The matcher first checks exact clinic names, ignoring case and spaces at the start or end. It does not use fuzzy name matching: abbreviations, punctuation and branch-name differences can leave a clinic unmatched.</p>
        <p className="mt-2">Address matching can also use the same Singapore postal code and unit number, or block and unit where postal matching is unavailable. Both records need the relevant address fields. Without address details, matching relies on names.</p>
        <p className="mt-2">Nearest alternatives need usable location data for the unmatched base clinics and candidate clinics in the comparison file. A valid postal code is the most reliable input; suggestions use straight-line distance.</p>
      </section>

      <section aria-labelledby="clinic-guide-results" className="max-w-prose">
        <h3 id="clinic-guide-results" className="text-base font-semibold text-gray-900">Read the results</h3>
        <dl className="mt-2 space-y-3">
          <div><dt className="font-semibold text-gray-900">Matched Clinics</dt><dd>Clinics found in both files, with the match method and address details.</dd></div>
          <div><dt className="font-semibold text-gray-900">Unmatched in Base</dt><dd>Base clinics not found in the comparison. With a panel master as base, these are panel clinics absent from the uploaded claims list.</dd></div>
          <div><dt className="font-semibold text-gray-900">Unmatched in Comparison</dt><dd>Comparison clinics not found in the base. With a panel master as base, these are claimed clinics not matched to the panel. Review naming differences before concluding they are outside the panel.</dd></div>
        </dl>
        <p className="mt-3">Optional file names change the report sheet labels. Exclusion filters apply to both files. Top 10/20 highlights a subset of base clinics after exclusions; all clinics are still compared.</p>
        <p className="mt-2">After uploading, check that “Clinics detected” is sensible for both files before selecting Match Clinics. If it shows 0, check the Clinic Name header and remove unrelated sheets or headings.</p>
      </section>
    </div>
  </details>
);

export default ClinicMatcherGuide;
