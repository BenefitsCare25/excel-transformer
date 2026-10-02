import React from 'react';

const money = (value) => Number(value).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function FlexPolicyChoices({ employees, decisions = {}, onChange, disabled, readOnly = false }) {
  if (!employees?.length) return null;
  const choiceFor = (employee) => readOnly ? employee.decision : decisions[employee.employee_id];
  const included = employees.filter((employee) => choiceFor(employee) === 'include');
  const excluded = employees.filter((employee) => choiceFor(employee) === 'exclude');
  return (
    <section className="mb-6 p-4 border border-amber-200 rounded-lg bg-amber-50 text-sm text-amber-900" aria-label={readOnly ? 'Employee choices used in these reports' : 'Choose employees for these reports'}>
      <h4 className="font-semibold">{readOnly ? 'Employee choices used in these reports' : 'Include or exclude these employees?'}</h4>
      {!readOnly && <>
        <p className="mt-2">Their benefits started before the selected policy period. Choose separately for each employee.</p>
        <p className="mt-2"><strong>Include</strong> keeps their claims and utilisation record in all three reports. <strong>Exclude</strong> removes both and reduces the report totals. The uploaded files stay unchanged.</p>
      </>}
      <div className="mt-3 divide-y divide-amber-200">
        {employees.map((employee) => (
          <fieldset key={employee.employee_id} disabled={disabled} className="min-w-0 py-3">
            <legend className="pt-2 font-semibold break-words">{employee.employee_id} · {employee.name}</legend>
            <p>Benefit start: {employee.benefit_start} · Policy starts: {employee.policy_start}</p>
            <p className="mt-1">{employee.claims} claim{employee.claims === 1 ? '' : 's'} · SGD {money(employee.amount)}</p>
            {readOnly ? <p className="mt-2 font-semibold">{employee.decision === 'include' ? 'Included in all three reports' : 'Excluded from all three reports'}</p> : (
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
                {['include', 'exclude'].map((choice) => (
                  <label key={choice} className="inline-flex items-center gap-2 py-2 cursor-pointer">
                    <input type="radio" name={`policy-${employee.employee_id}`} value={choice}
                      checked={choiceFor(employee) === choice}
                      onChange={() => onChange(employee.employee_id, choice)}
                      className="h-4 w-4 accent-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" />
                    {choice === 'include' ? 'Include in reports' : 'Exclude from reports'}
                  </label>
                ))}
              </div>
            )}
          </fieldset>
        ))}
      </div>
      <p className="mt-2 font-medium" role="status">
        {included.length} included · {excluded.length} excluded
        {!readOnly && ` · ${employees.length - included.length - excluded.length} still to choose`}
      </p>
      {excluded.length > 0 && <p className="mt-1">Excluded claims: SGD {money(excluded.reduce((sum, employee) => sum + employee.amount, 0))}. This amount is left out of the report totals.</p>}
    </section>
  );
}
