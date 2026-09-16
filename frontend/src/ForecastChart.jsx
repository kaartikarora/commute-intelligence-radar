import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
function ForecastChart({ results }) {
  const times = results[0].forecast.map((point) => point.time)
  const chartData = times.map((time, i) => {
    const row = { time }
    results.forEach((vehicle) => {
      row[vehicle.vehicle] = vehicle.forecast[i].price
    })
    return row
  })
    return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" />
        <YAxis />
        <Tooltip />
        <Legend />
        {results.map((vehicle) => (
          <Line
            key={vehicle.vehicle}
            type="monotone"
            dataKey={vehicle.vehicle}
            stroke={
              vehicle.vehicle === 'Auto' ? '#8884d8' :
              vehicle.vehicle === 'Non-AC' ? '#82ca9d' : '#ffc658'
            }
            dot={{ r: 3 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export default ForecastChart