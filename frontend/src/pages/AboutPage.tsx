import { Link } from 'react-router-dom'

export default function AboutPage() {
  return (
    <main className="page narrow">
      <h1>About Us</h1>
      <p>
        Campus Customs makes Yale apparel for everyone who bleeds Bulldog blue: students, alumni,
        families and fans. Our shop carries hoodies, crewnecks, T-shirts, quarter-zips and jackets
        for Yale, its residential colleges and its varsity teams.
      </p>
      <p>
        Every price and stock count on this site comes straight from our inventory, so what you see
        is what we have. Can’t find the right size or style? Ask the chat assistant in the bottom
        right corner. It can search the catalogue, check sizes and pull up matching items for you.
      </p>

      <h2>Come visit us</h2>
      <address className="store-address">
        Campus Customs
        <br />
        57 Broadway
        <br />
        New Haven, CT 06511
      </address>

      <p>
        <Link to="/products" className="button">
          Browse products
        </Link>
      </p>
    </main>
  )
}
