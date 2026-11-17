import React, { useState } from 'react';
import RenewalComparison from './RenewalComparison';
import RenewalAdjListing from './RenewalAdjListing';
import './Renewal.css';

const STORAGE_KEY = 'renewal.template';
const TEMPLATES = [
  {
    id: 'breakdown',
    title: 'Adjustment Breakdown',
    description: 'One sheet per product with cancel and re-enrol rows, divided by a pro-rata divisor.',
    io: 'Employee Listing YYYY → Summary + one sheet per product',
  },
  {
    id: 'adj-listing',
    title: 'Combined Adj Listing',
    description: 'Both policy years in one Adj sheet, adjusted by ÷365 × days, with an invoice summary per entity.',
    io: 'Classic or flat listing → Adj + Invoice Summary + Notes',
  },
];

const readSaved = () => {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return TEMPLATES.some((t) => t.id === saved) ? saved : TEMPLATES[0].id;
  } catch {
    return TEMPLATES[0].id;
  }
};

const RenewalTab = () => {
  const [template, setTemplate] = useState(readSaved);

  const choose = (id) => {
    setTemplate(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* storage blocked: the choice still applies for this visit */
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2" role="group" aria-label="Renewal report template">
        {TEMPLATES.map((t) => (
          <button
            key={t.id}
            type="button"
            aria-pressed={template === t.id}
            className={`renewal-picker ${template === t.id ? 'is-selected' : ''}`}
            onClick={() => choose(t.id)}
          >
            <span className="renewal-picker-title block">{t.title}</span>
            <span className="block text-sm renewal-muted mt-1">{t.description}</span>
            <span className="renewal-picker-io block">{t.io}</span>
          </button>
        ))}
      </div>
      <div hidden={template !== 'breakdown'}><RenewalComparison /></div>
      <div hidden={template !== 'adj-listing'}><RenewalAdjListing /></div>
    </div>
  );
};

export default RenewalTab;
