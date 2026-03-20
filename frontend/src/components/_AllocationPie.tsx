"use client";

import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

interface DataItem {
  name: string;
  pct: number;
  value: number;
  fill: string;
}

interface Props {
  data: DataItem[];
}

export default function AllocationPie({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={70}
          outerRadius={100}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((item, i) => (
            <Cell key={i} fill={item.fill} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [`${Number(value).toFixed(1)}%`]}
          contentStyle={{
            backgroundColor: "#18181b",
            border: "1px solid #3f3f46",
            borderRadius: "0.5rem",
            color: "#e4e4e7",
          }}
        />
        <Legend
          formatter={(value) => {
            const item = data.find((d) => d.name === value);
            return `${value}${item ? ` (${item.pct}%)` : ""}`;
          }}
          wrapperStyle={{ fontSize: "12px", color: "#a1a1aa" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
