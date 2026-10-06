import React from 'react';
import FlexValidationMessage from './FlexValidationMessage';
import './FlexClaimValidation.css';

const FIELD_LABELS = {
  TAX: 'Taxable (TAX)', CPF: 'CPF payable (CPF)', Relation: 'Relationship to employee (Relation)',
};
const LGI_NOTES = 'Self means employee; Spouse, Child and Parent match the eligibility columns in the checklist. Other Benefit is taxable and CPF-payable; its claimant eligibility rule has not been specified.';

function ClaimIssues({ issues, label, review = false }) {
  return (
    <div className={`flex-claim-table ${review ? 'review' : ''}`} tabIndex={0} role="region"
      aria-label={review ? 'CPF differences to review' : 'Claims requiring correction'}>
      <table className="w-full text-sm text-left">
        <caption className="sr-only">{review ? 'CPF flags preserved for review' : 'Claims requiring correction'}. Row numbers include the header row.</caption>
        <thead className="sticky top-0">
          <tr>{['Row / reference', 'Claim type', review ? 'Review needed' : 'Correction needed'].map((heading) => (
            <th key={heading} scope="col" className="p-3">{heading}</th>
          ))}</tr>
        </thead>
        <tbody>
          {issues.map((issue, index) => (
            <tr key={`${issue.row}-${issue.field}-${index}`}>
              <th scope="row" className="p-3 align-top font-medium">
                <span className="block whitespace-nowrap">Row {issue.row}</span>
                <span className="block break-words mt-1">{issue.reference || 'Missing reference'}</span>
              </th>
              <td className="p-3 align-top break-words">{issue.claim_type || 'Blank claim type'}</td>
              <td className="p-3 align-top break-words">
                <p className="font-medium">{FIELD_LABELS[issue.field] || issue.field}: {issue.actual || 'Not filled in'}</p>
                <p className="mt-1">{label} table: {issue.expected}</p>
                <p className="mt-1 flex-claim-muted">{issue.message}</p>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClaimRules({ rules, label, checkRelations, notes }) {
  const hasCodes = rules.some((rule) => rule.code);
  const columns = ['Claim type', 'Taxable', 'CPF payable', ...(checkRelations ? ['Eligible claimants'] : []),
    ...(hasCodes ? ['Code', 'Code description'] : [])];
  return (
    <details className="text-sm">
      <summary className="flex-claim-link cursor-pointer w-fit py-2 font-medium">
        View {label} tax, CPF{checkRelations ? ' and eligibility' : ' and payroll code'} rules
      </summary>
      <p className="my-2">{notes}</p>
      <div className="flex-claim-table rules" tabIndex={0} role="region" aria-label={`${label} checklist rules`}>
        <table className="w-full text-sm text-left">
          <caption className="sr-only">{label} benefit classification{checkRelations ? ' and eligible claimant relations' : ' and payroll codes'}</caption>
          <thead className="sticky top-0"><tr>{columns.map((heading) => (
            <th key={heading} scope="col" className="p-3">{heading}</th>
          ))}</tr></thead>
          <tbody>{rules.map((rule) => (
            <tr key={rule.claim_type}>
              <th scope="row" className="p-3 font-normal">{rule.claim_type}</th>
              <td className="p-3">{rule.taxable}</td>
              <td className="p-3">{rule.cpf}</td>
              {checkRelations && <td className="p-3">{rule.relations?.join(', ') ?? 'Not specified'}</td>}
              {hasCodes && <><td className="p-3 whitespace-nowrap">{rule.code}</td><td className="p-3">{rule.description}</td></>}
            </tr>
          ))}</tbody>
        </table>
      </div>
    </details>
  );
}

function ClaimStatus({ validation, label, checkRelations, inputStatus, onRetry }) {
  const issues = validation?.validation || [];
  const affectedClaims = new Set(issues.map((issue) => issue.row)).size;
  return (
    <div role="status" aria-live="polite" className="text-sm mb-3">
      {!validation && <p className="flex-claim-muted">Upload the claims workbook to check tax and CPF{checkRelations ? ' and claimant eligibility' : ''} against the {label} checklist.</p>}
      {validation?.status === 'checking' && <p>Checking the claims workbook…</p>}
      {validation?.status === 'valid' && <div>
        <p>Claim checks passed for {validation.claims} claims{validation.warnings?.length ? '; CPF differences are shown below for review' : ''}.</p>
        <p className={`mt-1 ${inputStatus === 'valid' ? 'flex-claim-success' : ''}`}>
          {inputStatus === 'valid' ? 'Employee details, dates and amounts also passed. Your files are ready.'
            : inputStatus === 'checking' ? 'Checking employee details, dates and amounts across your files…'
            : inputStatus === 'invalid' ? 'Some file checks still need attention. Review the message below before generating reports.'
            : 'Upload all required files to check employee details, dates and amounts before generating reports.'}
        </p>
      </div>}
      {validation?.status === 'invalid' && <div className="flex-claim-error p-3 rounded-lg">
        <p className="font-semibold">{affectedClaims} claim{affectedClaims === 1 ? '' : 's'} need{affectedClaims === 1 ? 's' : ''} attention before you can generate reports ({issues.length} correction{issues.length === 1 ? '' : 's'})</p>
        <p className="mt-1">Correct the rows below in the claims export, then upload the corrected workbook. All uploaded files stay selected while you review.</p>
      </div>}
      {validation?.status === 'error' && <div>
        <FlexValidationMessage feedback={validation.feedback || { title: 'We could not check your claims', message: validation.message }} />
        <button type="button" onClick={onRetry} className="flex-claim-link mt-2 underline underline-offset-2 font-medium">Check claims again</button>
      </div>}
    </div>
  );
}

export default function FlexClaimValidation({ validation, rules, config = {}, onRetry, inputStatus }) {
  const label = config.label || 'LGI';
  const checkRelations = config.check_relations !== false;
  const issues = validation?.validation || [];
  const warnings = validation?.warnings || [];
  return (
    <section className="flex-claim-checks mb-6 min-w-0" aria-labelledby="claim-checks-title">
      <h4 id="claim-checks-title" className="text-base font-semibold mb-2">{label} claim checks</h4>
      <ClaimStatus {...{ validation, label, checkRelations, inputStatus, onRetry }} />
      {issues.length > 0 && <ClaimIssues issues={issues} label={label} />}
      {warnings.length > 0 && <div className="mb-3">
        <p className="text-sm font-semibold mb-2">{warnings.length} CPF difference{warnings.length === 1 ? '' : 's'} to review — uploaded flags preserved</p>
        <ClaimIssues issues={warnings} label={label} review />
      </div>}
      <ClaimRules rules={rules} label={label} checkRelations={checkRelations} notes={config.notes || LGI_NOTES} />
    </section>
  );
}
