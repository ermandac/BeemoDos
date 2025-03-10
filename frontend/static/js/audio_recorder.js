document.addEventListener('DOMContentLoaded', function() {
    // Get all necessary DOM elements once, at script initialization
    const recordButton = document.getElementById('recordButton');
    const recordDuration = document.getElementById('recordDuration');
    const audioDeviceSelect = document.getElementById('audioDeviceSelect');
    const recordingStatus = document.getElementById('recordingStatus');

    // Validate that all critical elements exist
    const criticalElements = [
        { name: 'recordButton', element: recordButton },
        { name: 'recordDuration', element: recordDuration },
        { name: 'audioDeviceSelect', element: audioDeviceSelect },
        { name: 'recordingStatus', element: recordingStatus }
    ];

    const missingElements = criticalElements.filter(item => !item.element);
    if (missingElements.length > 0) {
        console.error('Missing critical DOM elements:', 
            missingElements.map(item => item.name).join(', ')
        );
        return;
    }

    // Predictors configuration
    const predictors = ['BNQ', 'QNQ', 'TOOT'];

    // Validate spectrogram elements before any processing
    function validateSpectrogramElements() {
        const missingSpectrogramElements = [];
        
        predictors.forEach(predictor => {
            const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
            const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
            const analysisContainer = document.getElementById(`analysisResults-${predictor}`);

            if (!imgElement) missingSpectrogramElements.push(`spectrogramImage-${predictor}-1`);
            if (!debugElement) missingSpectrogramElements.push(`spectrogramDebug-${predictor}-1`);
            if (!analysisContainer) missingSpectrogramElements.push(`analysisResults-${predictor}`);
        });

        return missingSpectrogramElements;
    }

    // Audio device selection
    const spectrogramContainers = {
        'BNQ': document.getElementById('spectrogramContainer-BNQ'),
        'QNQ': document.getElementById('spectrogramContainer-QNQ'),
        'TOOT': document.getElementById('spectrogramContainer-TOOT')
    };

    const spectrogramImages = {
        'BNQ': [
            document.getElementById('spectrogramImage-BNQ-1'),
            document.getElementById('spectrogramImage-BNQ-2'),
            document.getElementById('spectrogramImage-BNQ-3')
        ],
        'QNQ': [
            document.getElementById('spectrogramImage-QNQ-1'),
            document.getElementById('spectrogramImage-QNQ-2'),
            document.getElementById('spectrogramImage-QNQ-3')
        ],
        'TOOT': [
            document.getElementById('spectrogramImage-TOOT-1'),
            document.getElementById('spectrogramImage-TOOT-2'),
            document.getElementById('spectrogramImage-TOOT-3')
        ]
    };

    const analysisResultsContainers = {
        'BNQ': document.getElementById('analysisResults-BNQ'),
        'QNQ': document.getElementById('analysisResults-QNQ'),
        'TOOT': document.getElementById('analysisResults-TOOT')
    };

    // Fetch audio devices on page load
    function fetchAudioDevices() {
        // Log the full URL being fetched for debugging
        console.log('Fetching audio devices from:', window.location.origin + '/devices/');

        fetch('/devices/')  
            .then(response => {
                // Log the full response for debugging
                console.log('Response status:', response.status);
                console.log('Response headers:', Object.fromEntries(response.headers.entries()));

                // Check if the response is OK (status in the range 200-299)
                if (!response.ok) {
                    // If not OK, throw an error with status and statusText
                    throw new Error(`HTTP error! status: ${response.status}, message: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                // Check the status in the JSON response
                if (data.status === 'success') {
                    audioDeviceSelect.innerHTML = ''; // Clear existing options
                    if (data.devices && data.devices.length > 0) {
                        data.devices.forEach(device => {
                            const option = document.createElement('option');
                            option.value = device.index;
                            option.textContent = `${device.name} (${device.max_input_channels} channels)`;
                            audioDeviceSelect.appendChild(option);
                        });
                    } else {
                        // No input devices found
                        const option = document.createElement('option');
                        option.textContent = 'No input devices found';
                        option.disabled = true;
                        audioDeviceSelect.appendChild(option);
                        recordingStatus.textContent = 'Warning: No audio input devices detected';
                    }
                } else {
                    // Server returned an error status
                    throw new Error(data.message || 'Failed to fetch audio devices');
                }
            })
            .catch(error => {
                console.error('Error fetching audio devices:', error);
                
                // Update UI with error message
                audioDeviceSelect.innerHTML = ''; // Clear existing options
                const option = document.createElement('option');
                option.textContent = 'Error loading devices';
                option.disabled = true;
                audioDeviceSelect.appendChild(option);
                
                // Detailed error messaging
                recordingStatus.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error fetching audio devices:</strong> 
                        ${error.message}
                        <br>
                        Please check your audio setup and browser permissions.
                        <br>
                        <small>Debug Info: Attempted to fetch from /devices/</small>
                    </div>
                `;
            });
    }

    // Debugging function to log all spectrogram image elements
    function logSpectrogramElements() {
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        console.log('Spectrogram Image Elements:');
        predictors.forEach(predictor => {
            console.log(`${predictor} Images:`);
            spectrogramImages[predictor].forEach((img, index) => {
                console.log(`  Image ${index}:`, {
                    element: img,
                    src: img.src,
                    display: img.style.display,
                    naturalWidth: img.naturalWidth,
                    naturalHeight: img.naturalHeight
                });
            });
        });
    }

    // Diagnostic function to log all element details
    function logElementDetails() {
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        console.log('--- ELEMENT DIAGNOSTIC ---');
        predictors.forEach(predictor => {
            const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
            const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
            const analysisContainer = document.getElementById(`analysisResults-${predictor}`);
            
            console.log(`Predictor: ${predictor}`, {
                imgElement: {
                    exists: !!imgElement,
                    id: imgElement ? imgElement.id : 'NOT FOUND',
                    parentElement: imgElement ? imgElement.parentElement : 'NOT FOUND'
                },
                debugElement: {
                    exists: !!debugElement,
                    id: debugElement ? debugElement.id : 'NOT FOUND'
                },
                analysisContainer: {
                    exists: !!analysisContainer,
                    id: analysisContainer ? analysisContainer.id : 'NOT FOUND'
                }
            });
        });
    }

    // Comprehensive diagnostic function
    function logAllElementsInDocument() {
        console.log('--- COMPLETE DOCUMENT ELEMENT DIAGNOSTIC ---');
        
        // Log all elements with IDs matching our patterns
        const patterns = [
            /spectrogramImage-[A-Z]+-\d+/,
            /spectrogramDebug-[A-Z]+-\d+/,
            /analysisResults-[A-Z]+/
        ];

        patterns.forEach(pattern => {
            const matchingElements = Array.from(document.querySelectorAll('*'))
                .filter(el => el.id && pattern.test(el.id));
            
            console.log(`Elements matching ${pattern}:`, 
                matchingElements.map(el => ({
                    id: el.id,
                    tagName: el.tagName,
                    parentId: el.parentElement ? el.parentElement.id : 'NO PARENT'
                }))
            );
        });
    }

    function recordAudioForPredictors() {
        // First, validate spectrogram elements
        const missingElements = validateSpectrogramElements();
        if (missingElements.length > 0) {
            console.error('Missing spectrogram elements:', missingElements);
            recordingStatus.innerHTML = `
                <div class="alert alert-danger">
                    Error: Missing HTML elements: ${missingElements.join(', ')}
                </div>
            `;
            return;
        }

        // Detailed logging of ALL elements
        console.log('--- FULL ELEMENT DIAGNOSTIC ---');
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        predictors.forEach(predictor => {
            const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
            const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
            const analysisContainer = document.getElementById(`analysisResults-${predictor}`);

            console.log(`Predictor: ${predictor}`, {
                imgElement: {
                    exists: !!imgElement,
                    id: imgElement ? imgElement.id : 'NULL',
                    parentId: imgElement && imgElement.parentElement ? imgElement.parentElement.id : 'NO PARENT'
                },
                debugElement: {
                    exists: !!debugElement,
                    id: debugElement ? debugElement.id : 'NULL'
                },
                analysisContainer: {
                    exists: !!analysisContainer,
                    id: analysisContainer ? analysisContainer.id : 'NULL'
                }
            });
        });

        // Get recording duration and selected device
        const duration = parseFloat(recordDuration.value);
        const deviceIndex = parseInt(audioDeviceSelect.value);

        // Validate inputs
        if (isNaN(duration) || duration <= 0) {
            recordingStatus.innerHTML = `
                <div class="alert alert-danger">
                    Please enter a valid recording duration.
                </div>
            `;
            return;
        }

        // Defensive programming: use safe element access
        const safeGetElement = (id) => {
            const element = document.getElementById(id);
            if (!element) {
                console.error(`CRITICAL: Element with ID ${id} not found!`);
                throw new Error(`Missing element: ${id}`);
            }
            return element;
        };

        try {
            // Reset previous spectrograms and results
            predictors.forEach(predictor => {
                const imgElement = safeGetElement(`spectrogramImage-${predictor}-1`);
                const debugElement = safeGetElement(`spectrogramDebug-${predictor}-1`);
                const analysisContainer = safeGetElement(`analysisResults-${predictor}`);
                
                // Clear previous state
                imgElement.src = ''; 
                imgElement.style.display = 'none';
                debugElement.innerHTML = 'Waiting for spectrogram...';
                analysisContainer.innerHTML = '';
            });
        } catch (error) {
            console.error('Fatal error during element preparation:', error);
            recordingStatus.innerHTML = `
                <div class="alert alert-danger">
                    Error: ${error.message}
                </div>
            `;
            return;
        }

        // Update UI to show recording in progress
        recordingStatus.innerHTML = `
            <div class="alert alert-info">
                Recording in progress for each predictor... Please wait.
            </div>
        `;
        recordButton.disabled = true;

        // Fetch multi-record endpoint
        fetch('/audio_analyzer/multi-record/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                duration: duration, 
                device_index: deviceIndex 
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}, message: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Extensive logging of response data
            console.log('Full response data:', JSON.stringify(data, null, 2));

            // Check if the response contains the expected data
            if (data.status === 'success') {
                // Log spectrogram URLs for debugging
                console.log('Spectrogram URLs:', JSON.stringify(data.spectrograms, null, 2));

                // Update spectrograms for each predictor
                predictors.forEach(predictor => {
                    // Get the first (and only) spectrogram path
                    const spectrogramPath = data.spectrograms[predictor][0];
                    
                    // Get the image and debug elements with additional error checking
                    const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
                    const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
                    const analysisContainer = document.getElementById(`analysisResults-${predictor}`);
                    
                    // Comprehensive null checks
                    if (!imgElement || !debugElement) {
                        console.error(`Missing elements for predictor: ${predictor}`);
                        return;
                    }
                    
                    // Detailed logging before setting image
                    console.log(`Attempting to set ${predictor} image:`, {
                        path: spectrogramPath,
                        element: imgElement,
                        parentElement: imgElement.parentElement
                    });

                    // Update debug info
                    debugElement.innerHTML = `Attempting to load: ${spectrogramPath}`;

                    // Set source and make visible with error handling
                    imgElement.onload = function() {
                        console.log(`Successfully loaded ${predictor} image`);
                        imgElement.style.display = 'block';
                        imgElement.style.maxWidth = '100%';
                        imgElement.style.height = 'auto';
                        debugElement.innerHTML = `Loaded successfully: ${spectrogramPath}`;
                    };
                    
                    imgElement.onerror = function() {
                        console.error(`Failed to load ${predictor} image:`, {
                            src: spectrogramPath,
                            element: imgElement
                        });
                        imgElement.style.display = 'none';
                        debugElement.innerHTML = `Failed to load image: ${spectrogramPath}`;
                    };

                    // Actually set the source
                    // Ensure the path starts with a forward slash
                    imgElement.src = spectrogramPath.startsWith('/') ? spectrogramPath : `/${spectrogramPath}`;

                    // Update analysis results if available
                    if (analysisContainer && data.analysis_results) {
                        console.log('Full Analysis Results:', JSON.stringify(data.analysis_results, null, 2));
                        
                        // Predictors to process
                        const predictors = ['BNQ', 'QNQ', 'TOOT'];
                        
                        predictors.forEach(predictor => {
                            try {
                                // Check if results exist for this predictor
                                let results = data.analysis_results[predictor];
                                
                                console.log(`Processing ${predictor} Results:`, JSON.stringify(results, null, 2));
                                
                                // Validate results object
                                if (!results) {
                                    console.warn(`No results found for ${predictor}`);
                                    return;
                                }
                                
                                // Extract confidence using helper function
                                const confidence = extractConfidence(results);
                                
                                // Prepare analysis HTML
                                let analysisHtml = `<h4>Analysis Results for ${predictor}</h4>`;
                                
                                // Detailed analysis display
                                analysisHtml += `
                                    <div class="analysis-details">
                                        <div class="row">
                                            <div class="col-md-6">
                                                <h5>Prediction Details</h5>
                                                <table class="table table-bordered">
                                                    <tr>
                                                        <th>Prediction</th>
                                                        <td>${results.label || 'Unknown'}</td>
                                                    </tr>
                                                    <tr>
                                                        <th>Confidence</th>
                                                        <td>${formatConfidence(confidence)}</td>
                                                    </tr>
                                                </table>
                                            </div>
                                            <div class="col-md-6">
                                                <h5>Recommended Actions</h5>
                                                <div class="alert ${getAlertClass(predictor, results)}">
                                                    ${getRecommendedAction(predictor, results)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `;
                                
                                // Find the specific analysis container for this predictor
                                const specificAnalysisContainer = document.getElementById(`analysisResults-${predictor}`);
                                if (specificAnalysisContainer) {
                                    specificAnalysisContainer.innerHTML = analysisHtml;
                                } else {
                                    console.warn(`No container found for ${predictor} analysis results`);
                                }
                            } catch (error) {
                                console.error(`Error processing ${predictor} results:`, error);
                            }
                        });
                    } else {
                        console.warn('No analysis results found in response', data);
                    }
                });

                // Update recording status
                recordingStatus.innerHTML = `
                    <div class="alert alert-success">
                        Recording and analysis completed successfully!
                    </div>
                `;
            } else {
                // Handle server-side error
                throw new Error(data.message || 'Failed to record and analyze audio');
            }
        })
        .catch(error => {
            console.error('Error recording audio:', error);
            
            // Update UI with error message
            recordingStatus.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error recording audio:</strong> 
                    ${error.message}
                    <br>
                    Please check your audio setup and try again.
                </div>
            `;
        })
        .finally(() => {
            // Re-enable record button
            recordButton.disabled = false;
        });
    }

    // Detailed confidence extraction function
    function extractConfidence(results) {
        console.group('Confidence Extraction Debug');
        console.log('Input Results:', JSON.stringify(results, null, 2));

        let confidence;
        
        // Check if results is the correct object or if it's a metadata object
        if (results.analysis_results) {
            console.log('Found nested analysis_results, extracting from there');
            results = results.analysis_results;
        }

        // Try multiple methods to extract confidence
        if (results.confidence !== undefined) {
            confidence = results.confidence;
            console.log('Extracted from results.confidence');
        } else if (results.raw_result && results.raw_result[1] !== undefined) {
            confidence = results.raw_result[1];
            console.log('Extracted from raw_result[1]');
        } else if (results.predicted_class !== undefined) {
            // Fallback to prediction class if no direct confidence
            confidence = results.predicted_class === 1 ? 0.5 : 0.0;
            console.log('Fallback to prediction class');
        } else {
            confidence = undefined;
            console.warn('No confidence could be extracted');
        }

        console.log('Extracted Confidence:', confidence);
        console.log('Confidence Type:', typeof confidence);
        console.groupEnd();

        return confidence;
    }

    // Helper function to get prediction label
    function getPredictionLabel(predictor, results) {
        const predictionMap = {
            'BNQ': results.confidence > 0.5 ? 'Bees Detected' : 'No Bees Detected',
            'QNQ': results.confidence > 0.5 ? 'Queen Detected' : 'No Queen Detected',
            'TOOT': results.confidence > 0.5 ? 'Tooting Detected' : 'No Tooting'
        };
        return predictionMap[predictor] || 'Unknown';
    }

    // Helper function to format confidence level
    function formatConfidence(confidence) {
        // Extensive logging for debugging
        console.log('Raw Confidence Input:', confidence);
        console.log('Typeof Confidence:', typeof confidence);

        // Check if confidence is a valid number
        if (confidence === undefined || confidence === null) {
            console.warn('Confidence is undefined or null');
            return 'N/A';
        }

        // Ensure confidence is a number and round to 2 decimal places
        const formattedConfidence = Number(confidence).toFixed(2);
        
        console.log('Formatted Confidence:', formattedConfidence);

        // Add percentage sign and color coding
        if (formattedConfidence > 50) {
            return `<span class="text-success">${formattedConfidence}%</span>`;
        } else if (formattedConfidence > 25) {
            return `<span class="text-warning">${formattedConfidence}%</span>`;
        } else {
            return `<span class="text-danger">${formattedConfidence}%</span>`;
        }
    }

    // Helper function to get alert class
    function getAlertClass(predictor, results) {
        return results.confidence > 0.5 
            ? 'alert-warning' 
            : 'alert-info';
    }

    // Helper function to get recommended action
    function getRecommendedAction(predictor, results) {
        const actionMap = {
            'BNQ': {
                positive: 'Hive Activity Confirmed. Continue regular monitoring.',
                negative: 'No buzzing detected. Inspect the hive for potential issues.'
            },
            'QNQ': {
                positive: 'Queen Bee Presence Confirmed. Hive appears stable.',
                negative: 'Queen Bee Might Be Absent. Prepare to introduce a new queen if necessary.'
            },
            'TOOT': {
                positive: 'Queen Tooting Detected. Potential queen emergence or competition.',
                negative: 'No queen tooting detected. Continue monitoring.'
            }
        };

        const actions = actionMap[predictor] || {};
        return results.confidence > 0.5 
            ? actions.positive || 'Positive detection' 
            : actions.negative || 'Negative detection';
    }

    // Helper function to render analysis results in a structured way
    function renderAnalysisResults(results) {
        if (typeof results !== 'object') {
            return `<p class="text-muted">No detailed analysis available</p>`;
        }

        let html = '<table class="table table-striped table-bordered">';
        html += '<thead><tr><th>Metric</th><th>Value</th></tr></thead>';
        html += '<tbody>';

        for (const [key, value] of Object.entries(results)) {
            let formattedValue = formatAnalysisValue(value);
            html += `
                <tr>
                    <td class="fw-bold">${formatKey(key)}</td>
                    <td>${formattedValue}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        return html;
    }

    // Format keys to be more readable
    function formatKey(key) {
        return key
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }

    // Format values to be more readable
    function formatAnalysisValue(value) {
        if (value === null || value === undefined) {
            return '<span class="text-muted">N/A</span>';
        }

        if (typeof value === 'boolean') {
            return value 
                ? '<span class="text-success">Yes</span>' 
                : '<span class="text-danger">No</span>';
        }

        if (typeof value === 'number') {
            return value.toFixed(2);
        }

        if (Array.isArray(value)) {
            return value.join(', ');
        }

        return String(value);
    }

    // Add spectrogram zoom functionality
    function setupSpectrogramZoom() {
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        const enlargedSpectrogramImage = document.getElementById('enlargedSpectrogramImage');
        
        predictors.forEach(predictor => {
            const spectrogramImage = document.getElementById(`spectrogramImage-${predictor}-1`);
            
            if (spectrogramImage) {
                spectrogramImage.addEventListener('click', function() {
                    // Set the enlarged image source to the current spectrogram
                    enlargedSpectrogramImage.src = this.src;
                    
                    // Use Bootstrap's modal to show the enlarged image
                    $('#spectrogramModal').modal('show');
                });
            }
        });
    }

    // Initialize page
    fetchAudioDevices();

    // Attach event listener to record button
    recordButton.addEventListener('click', recordAudioForPredictors);

    // Call setup function after other initializations
    setupSpectrogramZoom();
});
