import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ArrowDown, ArrowRight, CarFront, Check, CircleAlert, Gauge, LoaderCircle, ShieldCheck, Sparkles } from "lucide-react";
import { NumericInput } from "./components/NumericInput";
import { SelectInput } from "./components/SelectInput";
import { fetchOptions, predictPrice } from "./services/api";
import type { ApiOptions, CompanyOption, PredictionRequest, PredictionResponse } from "./types";

type FormState = {
  company: string;
  model: string;
  year_of_purchase: string;
  fuel_type: string;
  transmission: string;
  owner_type: string;
  city: string;
  seller_type: string;
  km_driven: string;
  mileage: string;
  seating_capacity: string;
  horsepower: string;
  engine_cc: string;
};

const EMPTY_FORM: FormState = {
  company: "", model: "", year_of_purchase: "", fuel_type: "", transmission: "", owner_type: "", city: "", seller_type: "", km_driven: "", mileage: "",
  seating_capacity: "", horsepower: "", engine_cc: "",
};

export default function App() {
  const [options, setOptions] = useState<ApiOptions | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchOptions()
      .then((value) => {
        if (!active) return;
        setOptions(value);
        if (![value.fuel_options, value.transmission_options, value.owner_options, value.city_options, value.seller_options].every(Array.isArray)) {
          setError("The prediction API is still running an older version. Restart the backend, then refresh this page.");
        }
      })
      .catch((reason: Error) => { if (active) setError(reason.message); })
      .finally(() => { if (active) setLoadingOptions(false); });
    return () => { active = false; };
  }, []);

  const selectedCompany = useMemo(
    () => options?.companies.find((company) => company.value === form.company),
    [form.company, options],
  );

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setError("");
    setResult(null);
  }

  function changeCompany(value: string) {
    setForm((current) => ({ ...current, company: value, model: "" }));
    setError("");
    setResult(null);
  }

  function getCompanyLabel(companyValue: string, list: CompanyOption[]) {
    return list.find((company) => company.value === companyValue)?.label || companyValue;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!options) {
      setError("Vehicle options are not available yet. Check the connection and reload the page.");
      return;
    }
    const formElement = event.currentTarget;
    if (!formElement.reportValidity()) return;
    const input: PredictionRequest = {
      company: form.company,
      model: form.model,
      year_of_purchase: Number(form.year_of_purchase),
      fuel_type: form.fuel_type,
      transmission: form.transmission,
      owner_type: form.owner_type,
      city: form.city,
      seller_type: form.seller_type,
      km_driven: Number(form.km_driven),
      mileage: Number(form.mileage),
      seating_capacity: Number(form.seating_capacity),
      horsepower: Number(form.horsepower),
      engine_cc: Number(form.engine_cc),
    };
    setLoadingPrediction(true);
    try {
      const prediction = await predictPrice(input);
      setResult(prediction);
      window.setTimeout(() => document.getElementById("estimate-result")?.scrollIntoView({ behavior: "smooth", block: "center" }), 80);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Prediction failed. Please try again.");
    } finally {
      setLoadingPrediction(false);
    }
  }

  const companyDisabled = !options || loadingOptions;
  const modelDisabled = companyDisabled || !form.company || !selectedCompany?.models.length;

  return (
    <div className="min-h-screen overflow-hidden bg-ink text-white">
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />
      <header className="relative z-10 border-b border-white/[0.07]">
        <div className="mx-auto flex h-[76px] max-w-6xl items-center justify-between px-5 sm:px-8">
          <a href="#top" className="group flex items-center gap-3" aria-label="Car Value home">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-electric/25 bg-electric/10 text-electric transition group-hover:bg-electric/15">
              <CarFront size={22} strokeWidth={1.8} />
            </span>
            <span>
              <span className="block font-display text-sm font-extrabold tracking-[0.12em] text-white">MOTOR<span className="text-electric">MIND</span></span>
              <span className="block text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Car value estimator</span>
            </span>
          </a>
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-400 sm:flex">
            <a className="transition hover:text-white" href="#estimate">Estimate</a>
            <a className="transition hover:text-white" href="#how-it-works">How it works</a>
          </nav>
          <a href="#estimate" className="inline-flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-electric/50 hover:text-white">
            Get estimate <ArrowRight size={14} />
          </a>
        </div>
      </header>

      <main id="top" className="relative z-10 mx-auto max-w-6xl px-5 pb-20 sm:px-8">
        <section className="relative grid gap-10 pb-12 pt-14 sm:pb-16 sm:pt-20 lg:grid-cols-[1.3fr_.7fr] lg:items-end lg:gap-14">
          <div className="max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-electric/20 bg-electric/[0.08] px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.16em] text-blue-200">
              <Sparkles size={13} className="text-electric" /> Data-informed. Driver-ready.
            </div>
            <h1 className="max-w-3xl font-display text-4xl font-extrabold leading-[1.1] tracking-[-0.045em] text-white sm:text-5xl lg:text-[62px]">
              Find Your Car&apos;s<br className="hidden sm:block" /> Estimated <span className="text-electric">Value.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-slate-300 sm:text-lg sm:leading-8">
              A clearer starting point for your next move. Get an estimated used-car listing value from a machine learning model trained on real vehicle listings.
            </p>
            <a href="#estimate" className="mt-8 inline-flex items-center gap-2 text-sm font-bold text-white transition hover:text-blue-200">
              Build your estimate <ArrowDown size={16} className="text-electric" />
            </a>
          </div>
          <div className="relative hidden lg:block">
            <div className="hero-note ml-auto max-w-[320px] rounded-2xl border border-white/[0.08] bg-white/[0.035] p-5">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-electric/10 text-electric"><Gauge size={20} /></div>
              <p className="font-display text-lg font-bold text-white">Your car has a story.</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">Age, mileage, engine details and the exact model all shape its estimate.</p>
              <div className="mt-5 flex items-center gap-2 border-t border-white/[0.08] pt-4 text-xs text-slate-400"><ShieldCheck size={15} className="text-emerald-400" /> Built from the supplied listing dataset</div>
            </div>
          </div>
        </section>

        <section id="estimate" className="scroll-mt-8">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-electric">The estimate</p>
              <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">Tell us about your car</h2>
              <p className="mt-2 text-sm text-slate-400">Vehicle details shaped by the car, its ownership, and where it is listed.</p>
            </div>
            {options && <div className="hidden items-center gap-2 pb-1 text-xs text-slate-500 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Vehicle catalog ready</div>}
          </div>

          <div className="rounded-2xl border border-white/[0.09] bg-panel/90 p-5 shadow-card backdrop-blur sm:p-8">
            {loadingOptions ? (
              <div className="flex min-h-60 flex-col items-center justify-center gap-3 text-center text-slate-400">
                <LoaderCircle className="animate-spin text-electric" size={25} />
                <p className="text-sm">Loading vehicle options…</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <div className="mb-6 grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
                  <SelectInput
                    id="company" label="Company / Brand" placeholder="Select a manufacturer"
                    value={form.company} onChange={(event) => changeCompany(event.target.value)}
                    options={options?.companies.map(({ value, label }) => ({ value, label })) || []}
                    disabled={companyDisabled} autoComplete="off"
                  />
                  <SelectInput
                    id="car-model" label="Car Model" placeholder={form.company ? "Select a model" : "Choose a company first"}
                    value={form.model} onChange={(event) => update("model", event.target.value)}
                    options={selectedCompany?.models || []} disabled={modelDisabled} autoComplete="off"
                    hint={form.company ? "Models are filtered to the selected manufacturer." : "The model list appears after you choose a company."}
                  />
                  <NumericInput
                    id="purchase-year" label="Year of Purchase" unit="year"
                    value={form.year_of_purchase} onChange={(event) => update("year_of_purchase", event.target.value)}
                    min={1900} max={options?.reference_year} step={1}
                    placeholder="e.g. 2020" hint={`Vehicle age is calculated automatically using ${options?.reference_year ?? "the dataset"} as the reference year.`}
                  />
                  <SelectInput
                    id="fuel-type" label="Fuel Type" placeholder="Select fuel type"
                    value={form.fuel_type} onChange={(event) => update("fuel_type", event.target.value)}
                    options={options?.fuel_options?.map((value) => ({ value, label: value.replace(/\b\w/g, (letter) => letter.toUpperCase()) })) || []}
                    disabled={!options?.fuel_options?.length}
                  />
                  <SelectInput
                    id="transmission" label="Transmission" placeholder="Select transmission"
                    value={form.transmission} onChange={(event) => update("transmission", event.target.value)}
                    options={options?.transmission_options?.map((value) => ({ value, label: value.replace(/\b\w/g, (letter) => letter.toUpperCase()) })) || []}
                    disabled={!options?.transmission_options?.length}
                  />
                  <SelectInput
                    id="owner-type" label="Ownership" placeholder="Select owner count"
                    value={form.owner_type} onChange={(event) => update("owner_type", event.target.value)}
                    options={options?.owner_options?.map((value) => ({
                      value,
                      label: value === "unregistered car" ? "Unregistered" : `${value.replace(/\b\w/g, (letter) => letter.toUpperCase())} Owner`,
                    })) || []}
                    disabled={!options?.owner_options?.length}
                    hint="Select the number of previous owners."
                  />
                  <SelectInput
                    id="city" label="City / Location" placeholder="Select a city"
                    value={form.city} onChange={(event) => update("city", event.target.value)}
                    options={options?.city_options?.map((value) => ({ value, label: value.replace(/\b\w/g, (letter) => letter.toUpperCase()) })) || []}
                    disabled={!options?.city_options?.length}
                    hint="Estimates use listing cities represented in the training data."
                  />
                  <SelectInput
                    id="seller-type" label="Seller Type" placeholder="Select seller type"
                    value={form.seller_type} onChange={(event) => update("seller_type", event.target.value)}
                    options={options?.seller_options?.map((value) => ({ value, label: value.replace(/\b\w/g, (letter) => letter.toUpperCase()) })) || []}
                    disabled={!options?.seller_options?.length}
                  />
                  <NumericInput
                    id="km-driven" label="Kilometers Driven" unit="km"
                    value={form.km_driven} onChange={(event) => update("km_driven", event.target.value)}
                    min={1} step="any"
                    placeholder="e.g. 45,000" hint="Total distance shown on the odometer."
                  />
                  <NumericInput
                    id="mileage" label="Mileage" unit="km/l"
                    value={form.mileage} onChange={(event) => update("mileage", event.target.value)}
                    min={0.000001} step="any"
                    placeholder="e.g. 20.0" hint="Enter kilometres per litre as listed for your car."
                  />
                  <NumericInput
                    id="seating-capacity" label="Seating Capacity" unit="seats"
                    value={form.seating_capacity} onChange={(event) => update("seating_capacity", event.target.value)}
                    min={1} step={1} placeholder="e.g. 5" hint="Enter the number of seats in the car."
                  />
                  <NumericInput
                    id="horsepower" label="Engine Horsepower" unit="bhp"
                    value={form.horsepower} onChange={(event) => update("horsepower", event.target.value)}
                    min={0.000001} step="any"
                    placeholder="e.g. 88" hint="Power values are normalized to bhp."
                  />
                  <NumericInput
                    id="engine-cc" label="Engine Capacity" unit="cc"
                    value={form.engine_cc} onChange={(event) => update("engine_cc", event.target.value)}
                    min={0.000001} step="any"
                    placeholder="e.g. 1,197" hint="Engine displacement in cubic centimetres."
                  />
                </div>

                {error && (
                  <div role="alert" className="mb-5 flex items-start gap-3 rounded-xl border border-rose-400/20 bg-rose-400/[0.08] px-4 py-3 text-sm leading-6 text-rose-100">
                    <CircleAlert size={18} className="mt-0.5 shrink-0 text-rose-300" /> <span>{error}</span>
                  </div>
                )}

                <div className="flex flex-col gap-4 border-t border-white/[0.08] pt-6 sm:flex-row sm:items-center sm:justify-between">
                  <p className="max-w-md text-xs leading-5 text-slate-500">Your details are used only to generate this estimate. The result is based on the model&apos;s training data.</p>
                  <button
                    type="submit"
                    disabled={loadingPrediction || loadingOptions || !options || !options.fuel_options?.length || !options.transmission_options?.length}
                    className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-electric px-6 py-3 text-sm font-bold text-ink shadow-[0_8px_24px_rgba(99,165,255,.18)] transition hover:bg-blue-300 focus:outline-none focus:ring-2 focus:ring-electric focus:ring-offset-2 focus:ring-offset-panel disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loadingPrediction ? <><LoaderCircle size={17} className="animate-spin" /> Calculating…</> : <>Predict car price <ArrowRight size={17} /></>}
                  </button>
                </div>
              </form>
            )}
          </div>
        </section>

        {result && options && (
          <section id="estimate-result" aria-live="polite" className="mt-7 scroll-mt-8 rounded-2xl border border-electric/25 bg-[linear-gradient(135deg,rgba(35,75,125,.4),rgba(16,29,45,.96)_55%)] p-6 shadow-card sm:p-8">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-blue-200"><Check size={15} /> Estimated advertised value</div>
                <p className="mt-3 font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl">{result.formatted_price_inr}</p>
                <p className="mt-2 text-sm text-slate-400">Based on the details you provided</p>
              </div>
              <div className="rounded-xl border border-white/[0.1] bg-ink/40 p-4 sm:min-w-64">
                <p className="text-sm font-semibold text-white">{getCompanyLabel(result.inputs.company, options.companies)} {selectedCompany?.models.find((model) => model.value === result.inputs.model)?.label || result.inputs.model}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-400">
                  <span>Purchased {result.inputs.year_of_purchase}</span><span>{result.inputs.km_driven.toLocaleString("en-IN")} km driven</span>
                  <span>{result.inputs.fuel_type}</span><span>{result.inputs.transmission}</span>
                  <span>{result.inputs.owner_type} owner</span><span>{result.inputs.city}</span><span>{result.inputs.seller_type}</span>
                </div>
              </div>
            </div>
            <div className="mt-6 flex flex-col gap-3 border-t border-white/[0.09] pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="max-w-xl text-xs leading-5 text-slate-400">{result.disclaimer} Actual transaction prices vary with condition, service history, location and market timing.</p>
              <button type="button" onClick={() => { setResult(null); document.getElementById("estimate")?.scrollIntoView({ behavior: "smooth" }); }} className="inline-flex shrink-0 items-center gap-2 self-start text-sm font-bold text-blue-200 transition hover:text-white sm:self-auto">
                Edit details <ArrowRight size={15} />
              </button>
            </div>
          </section>
        )}

        <section id="how-it-works" className="mt-16 grid gap-6 border-t border-white/[0.08] pt-8 sm:grid-cols-3">
          <div><span className="text-xs font-bold uppercase tracking-[0.15em] text-electric">01 / Details</span><p className="mt-2 text-sm leading-6 text-slate-300">Choose the exact make, model, ownership history, location and seller, then enter the car&apos;s specifications.</p></div>
          <div><span className="text-xs font-bold uppercase tracking-[0.15em] text-electric">02 / Model</span><p className="mt-2 text-sm leading-6 text-slate-300">A trained regression pipeline evaluates the details against vehicle listing data.</p></div>
          <div><span className="text-xs font-bold uppercase tracking-[0.15em] text-electric">03 / Estimate</span><p className="mt-2 text-sm leading-6 text-slate-300">Use the result as a starting point for research, not as a promise of sale value.</p></div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-white/[0.07]">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-6 text-xs leading-5 text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>© {new Date().getFullYear()} MotorMind · Educational car value estimator</span>
          <span>Estimated listing price only. Not a professional valuation or guaranteed transaction price.</span>
        </div>
      </footer>
    </div>
  );
}
