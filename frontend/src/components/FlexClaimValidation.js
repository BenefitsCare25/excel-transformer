import React from 'react';

export default function FlexClaimValidation({ validation, rules, onRetry }) {
  const issues = validation?.validation || [];
  const affectedClaims = new Set(issues.map((issue) => issue.row)).size;

  return (
    <section className="mb-6 min-w-0" aria-labelledby="claim-checks-title">
      <h4 id="claim-checks-title" className="text-base font-semibold text-gray-800 mb-2">LGI claim checks</h4>
      <div role="status" aria-live="polite" className="text-sm mb-3">
        {!validation && <p className="text-gray-600">Upload the claims workbook to check tax, CPF and claimant eligibility against the LGI checklist.</p>}
        {validation?.status === 'checking' && <p className="text-blue-800">Checking the claims workbook…</p>}
        {validation?.status === 'valid' && (
          <p className="text-green-800">Tax, CPF and eligibility checks passed for {validation.claims} claims. File and reconciliation checks also run when generating reports.</p>
        )}
        {validation?.status === 'invalid' && (
          <div className="p-3 border border-red-200 rounded-lg bg-red-50 text-red-800">
            <p className="font-semibold">{issues.length} issue{issues.length === 1 ? '' : 's'} across {affectedClaims} claim{affectedClaims === 1 ? '' : 's'} — generation blocked</p>
            <p className="mt-1">Correct the rows below in the claims export, then upload the corrected workbook. All uploaded files stay selected while you review.</p>
          </div>
        )}
        {validation?.status === 'error' && (
          <div className="p-3 border border-red-200 rounded-lg bg-red-50 text-red-800">
            <p className="font-semibold">Claims have not been checked — generation blocked</p>
            <p className="mt-1 break-words">{validation.message}</p>
            <button type="button" onClick={onRetry} className="mt-2 underline underline-offset-2 font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2">
              Check claims again
            </button>
          </div>
        )}
      </div>
      {issues.length > 0 && (
        <div className="max-h-96 overflow-auto border border-gray-200 rounded-lg mb-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" tabIndex={0} role="region" aria-label="Claims requiring correction">
          <table className="w-full text-sm text-left text-gray-700">
            <caption className="sr-only">Every checklist issue in the claims workbook. Row numbers include the header row.</caption>
            <thead className="sticky top-0 bg-gray-100 text-gray-800">
              <tr>
                <th scope="col" className="p-3">Row / reference</th>
                <th scope="col" className="p-3">Claim type</th>
                <th scope="col" className="p-3">Correction needed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {issues.map((issue, index) => (
                <tr key={`${issue.row}-${issue.field}-${index}`}>
                  <th scope="row" className="p-3 align-top font-medium">
                    <span className="block whitespace-nowrap">Row {issue.row}</span>
                    <span className="block break-words mt-1">{issue.reference || 'Missing reference'}</span>
                  </th>
                  <td className="p-3 align-top break-words">{issue.claim_type || 'Blank claim type'}</td>
                  <td className="p-3 align-top break-words">
                    <p className="font-medium">{issue.field}: {issue.actual || 'Blank'}</p>
                    <p className="mt-1">Expected: {issue.expected}</p>
                    <p className="mt-1 text-gray-600">{issue.message}</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <details className="text-sm text-gray-700">
        <summary className="cursor-pointer w-fit py-2 font-medium text-blue-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600">View LGI tax, CPF and eligibility rules</summary>
        <p className="my-2">Self means employee; Spouse, Child and Parent match the eligibility columns in the checklist. Other Benefit is taxable and CPF-payable; its claimant eligibility rule has not been specified.</p>
        <div className="overflow-auto max-h-80 border border-gray-200 rounded-lg" tabIndex={0} role="region" aria-label="LGI checklist rules">
          <table className="w-full text-sm text-left">
            <caption className="sr-only">LGI benefit classification and eligible claimant relations</caption>
            <thead className="sticky top-0 bg-gray-100">
              <tr>
                {['Claim type', 'Taxable', 'CPF payable', 'Eligible claimants'].map((label) => <th key={label} scope="col" className="p-3">{label}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {rules.map((rule) => (
                <tr key={rule.claim_type}>
                  <th scope="row" className="p-3 font-normal">{rule.claim_type}</th>
                  <td className="p-3">{rule.taxable}</td>
                  <td className="p-3">{rule.cpf}</td>
                  <td className="p-3">{rule.relations?.join(', ') ?? 'Not specified'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
