/** A labelled input/textarea/select with optional hint and "required for" tag. */
export function Field({ label, name, hint, requiredFor, children, ...inputProps }) {
  const id = `field-${name}`;
  const control = children || (
    inputProps.type === 'textarea' ? (
      <textarea id={id} name={name} className="input resize-y" rows={4} {...inputProps} type={undefined} />
    ) : (
      <input id={id} name={name} className="input" {...inputProps} />
    )
  );
  return (
    <div>
      <label className="label" htmlFor={id}>
        <span>{label}</span>
        {requiredFor && <span className="text-fg2 font-normal text-[0.65rem]">{requiredFor}</span>}
      </label>
      {control}
      {hint && <p className="hint">{hint}</p>}
    </div>
  );
}
