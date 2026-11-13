// A thin framed panel with small square markers on its four corners.
export function Frame({ className = "", children, ...rest }) {
  return (
    <div className={`frame ${className}`} {...rest}>
      <i className="fc tl" aria-hidden="true" />
      <i className="fc tr" aria-hidden="true" />
      <i className="fc bl" aria-hidden="true" />
      <i className="fc br" aria-hidden="true" />
      {children}
    </div>
  );
}
