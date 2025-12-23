/**
 * ErrorMessage component - Displays field-level validation errors
 *
 * Provides consistent styling for inline error messages below form fields.
 */

export default function ErrorMessage({ error, className = '' }) {
  if (!error) return null;

  return (
    <div className={`text-red-400 text-sm mt-1 ${className}`}>
      {error}
    </div>
  );
}

/**
 * FieldError component - Wrapper for form field with error display
 *
 * Usage:
 * <FieldError error={errors.name}>
 *   <input ... />
 * </FieldError>
 */
export function FieldError({ error, children, className = '' }) {
  return (
    <div className={className}>
      {children}
      <ErrorMessage error={error} />
    </div>
  );
}

/**
 * RequiredIndicator component - Red asterisk for required fields
 */
export function RequiredIndicator({ className = '' }) {
  return (
    <span className={`text-red-400 ml-1 ${className}`} aria-label="Required">
      *
    </span>
  );
}

/**
 * FormField component - Complete form field with label, input, and error
 *
 * Usage:
 * <FormField
 *   label="Name"
 *   required
 *   error={errors.name}
 * >
 *   <input ... />
 * </FormField>
 */
export function FormField({ label, required, error, children, hint, className = '' }) {
  const hasError = !!error;

  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-300 mb-1">
          {label}
          {required && <RequiredIndicator />}
        </label>
      )}
      {hint && <p className="text-xs text-gray-500 mb-1">{hint}</p>}
      <div className={hasError ? 'ring-1 ring-red-500 rounded-lg' : ''}>
        {children}
      </div>
      <ErrorMessage error={error} />
    </div>
  );
}

/**
 * FormErrorSummary component - Displays a summary of all form errors
 *
 * Usage:
 * <FormErrorSummary errors={errors} title="Please fix the following errors:" />
 */
export function FormErrorSummary({ errors, title = 'Please correct the following errors:', className = '' }) {
  const errorMessages = Object.values(errors).filter(Boolean);

  if (errorMessages.length === 0) return null;

  return (
    <div className={`bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 ${className}`}>
      <h3 className="font-medium mb-2">{title}</h3>
      <ul className="list-disc list-inside space-y-1">
        {errorMessages.map((error, index) => (
          <li key={index}>{error}</li>
        ))}
      </ul>
    </div>
  );
}
