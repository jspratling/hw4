/** Problem 10: the school-spirit bar at the top of every page. */
export default function SpiritBar() {
  return (
    <div className="spirit-bar" role="note">
      <span className="spirit-pennant" aria-hidden="true" />
      <span className="spirit-text">Go Yale! Beat Harvard!</span>
      <span className="spirit-pennant flip" aria-hidden="true" />
    </div>
  )
}
