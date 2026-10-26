import { useState } from "react";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedFinding, setSelectedFinding] = useState(null);

  const [
    openResultExplanation,
    setOpenResultExplanation
  ] = useState(null);

  const [
    openAttentionMap,
    setOpenAttentionMap
  ] = useState(null);

  const [
    attentionMaps,
    setAttentionMaps
  ] = useState({});

  const [
    attentionLoading,
    setAttentionLoading
  ] = useState(null);

  const [
    attentionError,
    setAttentionError
  ] = useState("");


  const detectionExplanations = {
    Pneumonia:
      "From a medical perspective, pneumonia may appear on a chest X-ray as areas of increased opacity or consolidation in the lungs. In our system, the uploaded X-ray is resized and normalized before being processed by a DenseNet121 deep-learning model trained on chest X-ray images. The model learned visual patterns associated with pneumonia and detected similar patterns in this image. The model output was then compared with the validation threshold selected for Pneumonia. Because the result crossed that threshold, Pneumonia was marked as a possible finding for medical review.",

    Pneumothorax:
      "From a medical perspective, pneumothorax may appear on a chest X-ray as air outside the lung, changes in the visible lung border, or reduced lung markings near the chest wall. In our system, the uploaded X-ray is resized and normalized before being processed by a DenseNet121 deep-learning model trained on chest X-ray images. The model identified visual features similar to patterns it learned for pneumothorax. The model output was compared with the validation threshold selected for Pneumothorax. Because the result crossed that threshold, Pneumothorax was marked as a possible finding for medical review.",

    Effusion:
      "From a medical perspective, pleural effusion is a buildup of fluid around the lung and may appear on a chest X-ray as increased opacity near the lower chest or changes around the diaphragm and lung borders. In our system, the uploaded X-ray is resized and normalized before being analyzed by a DenseNet121 deep-learning model trained on chest X-ray images. The model found visual patterns similar to those it learned for pleural effusion. The result was then compared with the validation threshold selected for Effusion. Because it crossed that threshold, Effusion was marked as a possible finding for medical review.",

    Cardiomegaly:
      "From a medical perspective, cardiomegaly may appear on a chest X-ray as an enlarged cardiac silhouette relative to the width of the chest. In our system, the uploaded X-ray is resized and normalized before being processed by a DenseNet121 deep-learning model trained on chest X-ray images. The model identified visual features similar to patterns it learned for an enlarged heart. The model output was compared with the validation threshold selected for Cardiomegaly. Because the result crossed that threshold, Cardiomegaly was marked as a possible finding for medical review.",
  };


  const findingGuides = {
    Pneumonia: {
      description:
        "Pneumonia is an infection that causes inflammation in the lungs.",

      xray:
        "On a chest X-ray, it may appear as areas of increased opacity or consolidation.",

      whatToDo: [
        "Medical evaluation is recommended when pneumonia is suspected.",
        "Rest and adequate fluids may be helpful when appropriate.",
        "Do not start antibiotics without medical advice.",
      ],

      doctor:
        "A healthcare professional should be consulted, especially if symptoms are significant, persistent, or worsening.",

      urgent: [
        "Severe or rapidly worsening difficulty breathing",
        "Blue, gray, or unusually pale lips or skin",
        "New confusion or difficulty staying awake",
        "Significant chest pain",
        "Coughing up blood or severe deterioration",
      ],
    },

    Pneumothorax: {
      description:
        "Pneumothorax occurs when air enters the space between the lung and chest wall and may cause part of the lung to collapse.",

      xray:
        "A chest X-ray may show air outside the lung and separation between the lung edge and the chest wall.",

      whatToDo: [
        "A suspected pneumothorax should be medically evaluated.",
        "Treatment depends on its size and the person's symptoms.",
        "Some cases may require removal of trapped air by a medical team.",
      ],

      doctor:
        "Yes. A suspected pneumothorax should be assessed by a healthcare professional.",

      urgent: [
        "Sudden or severe shortness of breath",
        "Sudden or severe chest pain",
        "Difficulty speaking because of breathlessness",
        "Fainting, severe weakness, or confusion",
        "Blue, gray, or unusually pale lips or skin",
      ],
    },

    Effusion: {
      description:
        "Pleural effusion is an abnormal buildup of fluid in the space around the lungs.",

      xray:
        "Fluid may appear near the lower part of the chest and may obscure normal lung or diaphragm borders.",

      whatToDo: [
        "Medical evaluation is usually recommended.",
        "Treatment depends on the cause and amount of fluid.",
        "Large amounts of fluid causing breathing problems may require drainage.",
      ],

      doctor:
        "Yes. The underlying cause of pleural effusion should be evaluated medically.",

      urgent: [
        "Severe or rapidly worsening shortness of breath",
        "Significant chest pain",
        "Difficulty breathing at rest",
        "Fainting or new confusion",
        "Blue, gray, or unusually pale lips or skin",
      ],
    },

    Cardiomegaly: {
      description:
        "Cardiomegaly means that the heart appears enlarged. It is a finding rather than a specific disease.",

      xray:
        "The heart silhouette may appear larger than expected compared with the width of the chest.",

      whatToDo: [
        "An enlarged heart should be discussed with a healthcare professional.",
        "Additional evaluation may include an ECG, echocardiogram, blood tests, or other tests.",
        "Treatment depends on the underlying cause.",
      ],

      doctor:
        "Yes. Cardiomegaly should be medically evaluated, particularly when symptoms are present.",

      urgent: [
        "Chest pain",
        "Severe or sudden shortness of breath",
        "Fainting",
        "Severe weakness",
        "Fast or irregular heartbeat with chest pain or breathlessness",
      ],
    },
  };


  const resetAnalysis = () => {
    setResults(null);
    setError("");

    setOpenResultExplanation(null);
    setOpenAttentionMap(null);

    setAttentionMaps({});
    setAttentionLoading(null);
    setAttentionError("");
  };


  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    resetAnalysis();

    setSelectedFile(file);

    const imageUrl = URL.createObjectURL(file);
    setPreviewUrl(imageUrl);
  };


  const handleAnalyze = async () => {
    if (!selectedFile) {
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    setOpenResultExplanation(null);
    setOpenAttentionMap(null);

    setAttentionMaps({});
    setAttentionError("");

    try {
      const formData = new FormData();

      formData.append(
        "file",
        selectedFile
      );

      const response = await fetch(
        "/predict",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(
          "The server could not analyze the image."
        );
      }

      const data = await response.json();

      setResults(data);

    } catch (err) {
      console.error(err);

      setError(
        "Could not connect to the AI analysis server."
      );

    } finally {
      setLoading(false);
    }
  };


  const toggleResultExplanation = (finding) => {
    if (openResultExplanation === finding) {
      setOpenResultExplanation(null);
    } else {
      setOpenResultExplanation(finding);
    }
  };


  const handleAttentionMap = async (finding) => {
    if (openAttentionMap === finding) {
      setOpenAttentionMap(null);
      return;
    }

    if (attentionMaps[finding]) {
      setOpenAttentionMap(finding);
      return;
    }

    if (!selectedFile) {
      return;
    }

    setAttentionLoading(finding);
    setAttentionError("");
    setOpenAttentionMap(null);

    try {
      const formData = new FormData();

      formData.append(
        "file",
        selectedFile
      );

      formData.append(
        "finding",
        finding
      );

      const response = await fetch(
        "/gradcam",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(
          "Could not generate the AI attention map."
        );
      }

      const data = await response.json();

      setAttentionMaps(
        (previousMaps) => ({
          ...previousMaps,
          [finding]: data,
        })
      );

      setOpenAttentionMap(finding);

    } catch (err) {
      console.error(err);

      setAttentionError(
        "Could not generate the AI attention map."
      );

    } finally {
      setAttentionLoading(null);
    }
  };


  const handleFindingClick = (finding) => {
    if (selectedFinding === finding) {
      setSelectedFinding(null);
    } else {
      setSelectedFinding(finding);
    }
  };


  return (
    <div className="app">

      <header className="header">

        <h1>
          Smart X-Ray AI
        </h1>

        <p>
          AI-Assisted Chest X-Ray Analysis
        </p>

      </header>


      <main className="main-content">

        <section className="upload-card">

          <h2>
            Upload Chest X-Ray
          </h2>

          <p className="description">
            Upload a chest X-ray image to receive
            AI-assisted analysis for selected
            radiological findings.
          </p>


          <label className="upload-area">

            <span className="upload-icon">
              🩻
            </span>

            <span className="upload-text">
              Choose a chest X-ray image
            </span>

            <span className="file-types">
              PNG or JPEG
            </span>

            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={handleFileChange}
            />

          </label>


          {selectedFile && (
            <div className="selected-file">
              Selected file: {selectedFile.name}
            </div>
          )}


          {previewUrl && (
            <div className="preview-container">

              <img
                src={previewUrl}
                alt="Selected chest X-ray"
                className="xray-preview"
              />

            </div>
          )}


          <button
            className="analyze-button"
            disabled={
              !selectedFile ||
              loading
            }
            onClick={handleAnalyze}
          >
            {loading
              ? "Analyzing..."
              : "Analyze X-Ray"}
          </button>


          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

        </section>


        {results && (
          <section className="results-card">

            <h2>
              AI Analysis Result
            </h2>


            {results.no_selected_finding_detected ? (

              <div className="no-finding-result">

                <div className="result-icon">
                  ✓
                </div>

                <h3>
                  No selected finding detected
                </h3>

                <p>
                  The analysis did not identify
                  patterns associated with the four
                  conditions supported by this system.
                </p>

                <p className="small-warning">
                  This does not rule out other
                  conditions or replace medical
                  evaluation.
                </p>

              </div>

            ) : (

              <div className="possible-findings">

                <div className="possible-heading">

                  <div className="result-icon warning-icon">
                    !
                  </div>

                  <div>

                    <h3>
                      Possible finding
                      {results.detected_findings.length > 1
                        ? "s"
                        : ""} detected
                    </h3>

                    <p>
                      The following finding
                      {results.detected_findings.length > 1
                        ? "s were"
                        : " was"} identified for further
                      medical review.
                    </p>

                  </div>

                </div>


                {results.detected_findings.map(
                  (finding) => {

                    const isExplanationOpen =
                      openResultExplanation === finding;

                    const isAttentionOpen =
                      openAttentionMap === finding;

                    const mapData =
                      attentionMaps[finding];

                    const isMapLoading =
                      attentionLoading === finding;


                    return (
                      <div
                        className="detected-finding-card"
                        key={finding}
                      >

                        <div className="detected-finding-title">
                          {finding}
                        </div>


                        <p className="medical-review-text">
                          Please consult a healthcare
                          professional for clinical
                          evaluation.
                        </p>


                        <div className="result-buttons">

                          <button
                            className="explanation-button"
                            onClick={() =>
                              toggleResultExplanation(
                                finding
                              )
                            }
                          >
                            {isExplanationOpen
                              ? "Hide explanation"
                              : "How did the system reach this result?"}
                          </button>


                          <button
                            className="attention-button"
                            disabled={isMapLoading}
                            onClick={() =>
                              handleAttentionMap(
                                finding
                              )
                            }
                          >
                            {isMapLoading
                              ? "Generating map..."
                              : isAttentionOpen
                              ? "Hide AI Attention Map"
                              : "View AI Attention Map"}
                          </button>

                        </div>


                        {isExplanationOpen && (
                          <div className="detection-explanation">

                            <p>
                              {
                                detectionExplanations[
                                  finding
                                ]
                              }
                            </p>

                            <p className="explanation-note">
                              The system combines
                              deep-learning image analysis
                              with finding-specific decision
                              thresholds. The result is
                              intended for decision support
                              and does not confirm a medical
                              diagnosis.
                            </p>

                          </div>
                        )}


                        {isAttentionOpen && mapData && (
                          <div className="attention-map-container">

                            <h4>
                              AI Attention Map
                            </h4>


                            <img
                              src={
                                mapData.attention_map
                              }
                              alt={
                                `${finding} AI attention map`
                              }
                              className="attention-map-image"
                            />


                            <div className="attention-map-legend">

                              <span>
                                Lower influence
                              </span>

                              <div className="legend-gradient" />

                              <span>
                                Higher influence
                              </span>

                            </div>


                            <p className="attention-explanation">
                              The highlighted regions show
                              areas that influenced the AI
                              analysis for {finding}.
                            </p>

                            <p className="attention-warning">
                              The highlighted areas do not
                              confirm the exact location of
                              disease.
                            </p>

                          </div>
                        )}

                      </div>
                    );
                  }
                )}


                {attentionError && (
                  <div className="error-message">
                    {attentionError}
                  </div>
                )}

              </div>
            )}

          </section>
        )}


        <section className="info-card">

          <h2>
            Supported Findings
          </h2>

          <p className="info-description">
            Select a condition to learn more about it,
            what may appear on a chest X-ray,
            and when medical attention may be needed.
          </p>


          <div className="accordion">

            {Object.keys(
              findingGuides
            ).map(
              (finding) => {

                const isOpen =
                  selectedFinding === finding;

                const guide =
                  findingGuides[finding];


                return (
                  <div
                    className={
                      isOpen
                        ? "accordion-item open"
                        : "accordion-item"
                    }
                    key={finding}
                  >

                    <button
                      className="accordion-button"
                      onClick={() =>
                        handleFindingClick(
                          finding
                        )
                      }
                    >

                      <span className="accordion-title">
                        {finding}
                      </span>

                      <span className="accordion-symbol">
                        {isOpen ? "−" : "+"}
                      </span>

                    </button>


                    {isOpen && (
                      <div className="accordion-content">

                        <div className="detail-section">

                          <h4>
                            What is it?
                          </h4>

                          <p>
                            {guide.description}
                          </p>

                        </div>


                        <div className="detail-section">

                          <h4>
                            What may appear on the X-ray?
                          </h4>

                          <p>
                            {guide.xray}
                          </p>

                        </div>


                        <div className="detail-section">

                          <h4>
                            What should be done?
                          </h4>

                          <ul>

                            {guide.whatToDo.map(
                              (item, index) => (
                                <li key={index}>
                                  {item}
                                </li>
                              )
                            )}

                          </ul>

                        </div>


                        <div className="doctor-box">

                          <h4>
                            Should a doctor be consulted?
                          </h4>

                          <p>
                            {guide.doctor}
                          </p>

                        </div>


                        <div className="urgent-box">

                          <h4>
                            🚨 Seek urgent medical help if:
                          </h4>

                          <ul>

                            {guide.urgent.map(
                              (item, index) => (
                                <li key={index}>
                                  {item}
                                </li>
                              )
                            )}

                          </ul>

                        </div>

                      </div>
                    )}

                  </div>
                );
              }
            )}

          </div>

        </section>


        <div className="disclaimer">

          <strong>
            ⚠ Medical Disclaimer
          </strong>

          <p>
            Smart X-Ray AI is an educational
            decision-support prototype.
            It does not provide a medical diagnosis
            or replace professional medical care.
          </p>

        </div>

      </main>

    </div>
  );
}

export default App;