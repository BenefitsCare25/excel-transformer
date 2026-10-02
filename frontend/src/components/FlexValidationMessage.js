import React from 'react';

export default function FlexValidationMessage({ feedback, onRetry }) {
  return (
    <div role="alert" className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800 break-words">
      <p className="font-semibold">{feedback.title || 'We could not complete this step'}</p>
      <p className="mt-1">{feedback.message}</p>
      {feedback.employee_ids?.length > 0 && (
        <div className="mt-3">
          <p className="font-medium">Employee IDs to check ({feedback.employee_ids.length})</p>
          <ul className="mt-1 list-disc pl-5 max-h-40 overflow-auto" tabIndex={0} aria-label="Employee IDs to check">
            {feedback.employee_ids.map((id) => <li key={id}>{id}</li>)}
          </ul>
        </div>
      )}
      {feedback.guidance && <p className="mt-3">{feedback.guidance}</p>}
      {feedback.records?.length > 0 && (
        <div className="mt-3 overflow-auto max-h-64" tabIndex={0} role="region" aria-label="Employee policy dates to review">
          <table className="w-full min-w-[38rem] text-left">
            <caption className="sr-only">Uploaded utilisation records excluded by the current date check</caption>
            <thead><tr>{['Employee ID', 'Benefit start date', 'Hire date', 'Why excluded'].map((label) => <th scope="col" className="p-2" key={label}>{label}</th>)}</tr></thead>
            <tbody>{feedback.records.map((record, index) => <tr key={`${record.employee_id}-${index}`}>
              <th scope="row" className="p-2 font-medium">{record.employee_id}</th>
              <td className="p-2 whitespace-nowrap">{record.benefit_start}</td>
              <td className="p-2 whitespace-nowrap">{record.hire_date}</td>
              <td className="p-2">{record.reason}</td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
      <p className="mt-2">Your uploaded files stay selected while you review.</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-3 underline underline-offset-2 font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2">
          Check files again
        </button>
      )}
    </div>
  );
}
