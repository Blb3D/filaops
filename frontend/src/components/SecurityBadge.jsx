/**
 * SecurityBadge - Prominent security indicator for data privacy
 *
 * Shows one of three states:
 * - Gray: AI Disabled (no data sent anywhere)
 * - Green: Data Private (using Ollama - local processing only)
 * - Yellow/Orange: Cloud AI (using Anthropic - data sent externally)
 */
import { useState } from 'react';

const SecurityBadge = ({ aiProvider, externalBlocked }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  // Determine badge state
  let badgeColor, badgeText, icon, tooltipText;

  if (!aiProvider) {
    // AI Disabled
    badgeColor = 'bg-gray-700 border-gray-600 text-gray-400';
    badgeText = 'AI Disabled';
    icon = (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
    );
    tooltipText = 'AI features are disabled. No data is sent to any AI service.';
  } else if (aiProvider === 'ollama') {
    // Local processing - Data Private
    badgeColor = 'bg-green-900/50 border-green-500 text-green-400';
    badgeText = 'Data Private';
    icon = (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    );
    tooltipText = 'Using Ollama (local AI). All data stays on this machine. No external connections.';
  } else if (aiProvider === 'anthropic') {
    // Cloud AI - Warning
    badgeColor = 'bg-yellow-900/50 border-yellow-500 text-yellow-400';
    badgeText = 'Cloud AI';
    icon = (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
      </svg>
    );
    tooltipText = 'Using Anthropic Claude (cloud AI). Invoice/PO data is sent to Anthropic for processing.';
  }

  return (
    <div className="relative">
      <div
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border-2 cursor-help transition-all ${badgeColor}`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {icon}
        <span className="font-semibold text-sm">{badgeText}</span>
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 w-64 p-3 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50">
          <p className="text-sm text-gray-300">{tooltipText}</p>
          {externalBlocked && (
            <p className="text-xs text-green-400 mt-2 flex items-center gap-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
              External AI is blocked
            </p>
          )}
          {/* Arrow */}
          <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-gray-800" />
        </div>
      )}
    </div>
  );
};

export default SecurityBadge;
