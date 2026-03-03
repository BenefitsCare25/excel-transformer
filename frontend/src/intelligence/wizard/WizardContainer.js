import React from 'react';
import StepUpload from './Step1_Upload';
import StepSheetSelector from './Step2_SheetSelector';
import StepColumnMapper from './Step3_ColumnMapper';
import StepRuleBuilder from './Step4_RuleBuilder';
import StepOutputConfig from './Step5_OutputConfig';

const STEPS = [
  { num: 1, label: 'Upload' },
  { num: 2, label: 'Sheets' },
  { num: 3, label: 'Columns' },
  { num: 4, label: 'Rules' },
  { num: 5, label: 'Output' },
];

function StepIndicator({ currentStep, onGoTo }) {
  return (
    <div className="flex items-center justify-center mb-8">
      {STEPS.map((step, i) => (
        <React.Fragment key={step.num}>
          <button
            onClick={() => step.num < currentStep && onGoTo(step.num)}
            disabled={step.num >= currentStep}
            className={`flex flex-col items-center group ${step.num < currentStep ? 'cursor-pointer' : 'cursor-default'}`}
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
              step.num === currentStep
                ? 'bg-blue-600 text-white'
                : step.num < currentStep
                  ? 'bg-green-500 text-white group-hover:bg-green-600'
                  : 'bg-gray-200 text-gray-500'
            }`}>
              {step.num < currentStep ? '✓' : step.num}
            </div>
            <span className={`text-xs mt-1 ${step.num === currentStep ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
              {step.label}
            </span>
          </button>
          {i < STEPS.length - 1 && (
            <div className={`flex-1 h-0.5 mx-2 mb-4 transition-colors ${step.num < currentStep ? 'bg-green-400' : 'bg-gray-200'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function WizardContainer({ wizard, aiConfig }) {
  const { state, goToStep } = wizard;

  const stepProps = { wizard, aiConfig };

  return (
    <div>
      <StepIndicator currentStep={state.step} onGoTo={goToStep} />
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        {state.step === 1 && <StepUpload {...stepProps} />}
        {state.step === 2 && <StepSheetSelector {...stepProps} />}
        {state.step === 3 && <StepColumnMapper {...stepProps} />}
        {state.step === 4 && <StepRuleBuilder {...stepProps} />}
        {state.step === 5 && <StepOutputConfig {...stepProps} />}
      </div>
    </div>
  );
}
