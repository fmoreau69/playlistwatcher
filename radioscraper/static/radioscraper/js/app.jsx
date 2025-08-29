import React, { useState } from "react";
import { createRoot } from "react-dom/client";

function App() {
  const [country, setCountry] = useState("");
  const [state, setState] = useState("");
  const [tag, setTag] = useState("");
  const [radios, setRadios] = useState([]);

  const searchRadios = async () => {
    const params = new URLSearchParams();
    if (country) params.append("country", country);
    if (state) params.append("state", state);
    if (tag) params.append("tag", tag);

    const res = await fetch(`/radios/api/search/?${params.toString()}`);
    const data = await res.json();
    setRadios(data);
  };

  return (
    <div className="container mx-auto">
      <h1 className="text-2xl font-bold mb-4">🎶 RadioScraper</h1>

      <div className="flex gap-2 mb-4">
        <input
          className="border p-2 rounded"
          placeholder="Pays"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
        />
        <input
          className="border p-2 rounded"
          placeholder="Région"
          value={state}
          onChange={(e) => setState(e.target.value)}
        />
        <input
          className="border p-2 rounded"
          placeholder="Style"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
        />
        <button
          onClick={searchRadios}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          Rechercher
        </button>
      </div>

      <table className="table-auto border-collapse w-full bg-white shadow rounded">
        <thead>
          <tr className="bg-gray-200">
            <th className="p-2 border">Nom</th>
            <th className="p-2 border">Pays</th>
            <th className="p-2 border">Région</th>
            <th className="p-2 border">Style</th>
            <th className="p-2 border">Site web</th>
            <th className="p-2 border">Email</th>
          </tr>
        </thead>
        <tbody>
          {radios.map((r) => (
            <tr key={r.id} className="hover:bg-gray-100">
              <td className="p-2 border">{r.name}</td>
              <td className="p-2 border">{r.country}</td>
              <td className="p-2 border">{r.state}</td>
              <td className="p-2 border">{r.tags}</td>
              <td className="p-2 border">
                <a href={r.homepage} target="_blank" className="text-blue-600 underline">
                  {r.homepage}
                </a>
              </td>
              <td className="p-2 border">{r.emails}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const root = createRoot(document.getElementById("root"));
root.render(<App />);
