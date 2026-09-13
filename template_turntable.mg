{
    "header": {
        "releaseVersion": "2025.1.0",
        "fileVersion": "2.0",
        "nodesVersions": {
            "CameraInit": "12.0",
            "DepthMap": "5.0",
            "DepthMapFilter": "4.0",
            "FeatureExtraction": "1.3",
            "FeatureMatching": "2.0",
            "ImageDetectionPrompt": "0.1",
            "ImageMatching": "2.0",
            "ImageSegmentationBox": "0.2",
            "MeshDecimate": "1.0",
            "MeshFiltering": "3.0",
            "Meshing": "7.0",
            "PrepareDenseScene": "3.1",
            "StructureFromMotion": "3.3",
            "Texturing": "6.0"
        }
    },
    "graph": {
        "CameraInit_1": {
            "nodeType": "CameraInit",
            "position": [
                0,
                0
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 0,
                "split": 1
            },
            "uid": "4c471e04d91d618d3dddf7990cb9b81c599a7700",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "viewpoints": [],
                "intrinsics": [],
                "sensorDatabase": "${ALICEVISION_SENSOR_DB}",
                "lensCorrectionProfileInfo": "${ALICEVISION_LENS_PROFILE_INFO}",
                "lensCorrectionProfileSearchIgnoreCameraModel": true,
                "defaultFieldOfView": 45.0,
                "groupCameraFallback": "folder",
                "rawColorInterpretation": "LibRawWhiteBalancing",
                "colorProfileDatabase": "${ALICEVISION_COLOR_PROFILE_DB}",
                "errorOnMissingColorProfile": true,
                "viewIdMethod": "metadata",
                "viewIdRegex": ".*?(\\d+)",
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}/cameraInit.sfm"
            }
        },
        "DepthMapFilter_1": {
            "nodeType": "DepthMapFilter",
            "position": [
                1800,
                0
            ],
            "parallelization": {
                "blockSize": 24,
                "size": 0,
                "split": 0
            },
            "uid": "304d85299661b8f28ffcdef9138308ce0ff2ebae",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{DepthMap_1.input}",
                "depthMapsFolder": "{DepthMap_1.output}",
                "minViewAngle": 2.0,
                "maxViewAngle": 70.0,
                "nNearestCams": 10,
                "minNumOfConsistentCams": 3,
                "minNumOfConsistentCamsWithLowSimilarity": 4,
                "pixToleranceFactor": 2.0,
                "pixSizeBall": 0,
                "pixSizeBallWithLowSimilarity": 0,
                "computeNormalMaps": false,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "depth": "{nodeCacheFolder}/<VIEW_ID>_depthMap.exr",
                "sim": "{nodeCacheFolder}/<VIEW_ID>_simMap.exr",
                "normal": "{nodeCacheFolder}/<VIEW_ID>_normalMap.exr"
            }
        },
        "DepthMap_1": {
            "nodeType": "DepthMap",
            "position": [
                1600,
                0
            ],
            "parallelization": {
                "blockSize": 12,
                "size": 0,
                "split": 0
            },
            "uid": "6da696e3754ac3882acb2a91b38a9314938d420e",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{PrepareDenseScene_1.input}",
                "imagesFolder": "{PrepareDenseScene_1.output}",
                "downscale": 2,
                "minViewAngle": 2.0,
                "maxViewAngle": 70.0,
                "tiling": {
                    "tileBufferWidth": 1024,
                    "tileBufferHeight": 1024,
                    "tilePadding": 64,
                    "autoAdjustSmallImage": true
                },
                "chooseTCamsPerTile": true,
                "maxTCams": 10,
                "sgm": {
                    "sgmScale": 2,
                    "sgmStepXY": 2,
                    "sgmStepZ": -1,
                    "sgmMaxTCamsPerTile": 3,
                    "sgmWSH": 4,
                    "sgmUseSfmSeeds": true,
                    "sgmSeedsRangeInflate": 0.2,
                    "sgmDepthThicknessInflate": 0.0,
                    "sgmMaxSimilarity": 1.0,
                    "sgmGammaC": 5.5,
                    "sgmGammaP": 8.0,
                    "sgmP1": 10.0,
                    "sgmP2Weighting": 100.0,
                    "sgmMaxDepths": 1500,
                    "sgmFilteringAxes": "YX",
                    "sgmDepthListPerTile": true,
                    "sgmUseConsistentScale": false
                },
                "refine": {
                    "refineEnabled": true,
                    "refineScale": 1,
                    "refineStepXY": 1,
                    "refineMaxTCamsPerTile": 3,
                    "refineSubsampling": 10,
                    "refineHalfNbDepths": 15,
                    "refineWSH": 3,
                    "refineSigma": 15.0,
                    "refineGammaC": 15.5,
                    "refineGammaP": 8.0,
                    "refineInterpolateMiddleDepth": false,
                    "refineUseConsistentScale": false
                },
                "colorOptimization": {
                    "colorOptimizationEnabled": true,
                    "colorOptimizationNbIterations": 100
                },
                "customPatchPattern": {
                    "sgmUseCustomPatchPattern": false,
                    "refineUseCustomPatchPattern": false,
                    "customPatchPatternSubparts": [],
                    "customPatchPatternGroupSubpartsPerLevel": false
                },
                "intermediateResults": {
                    "exportIntermediateDepthSimMaps": false,
                    "exportIntermediateNormalMaps": false,
                    "exportIntermediateVolumes": false,
                    "exportIntermediateCrossVolumes": false,
                    "exportIntermediateTopographicCutVolumes": false,
                    "exportIntermediateVolume9pCsv": false,
                    "exportTilePattern": false
                },
                "nbGPUs": 0,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "depth": "{nodeCacheFolder}/<VIEW_ID>_depthMap.exr",
                "sim": "{nodeCacheFolder}/<VIEW_ID>_simMap.exr",
                "tilePattern": "{nodeCacheFolder}/<VIEW_ID>_tilePattern.obj",
                "depthSgm": "{nodeCacheFolder}/<VIEW_ID>_depthMap_sgm.exr",
                "depthSgmUpscaled": "{nodeCacheFolder}/<VIEW_ID>_depthMap_sgmUpscaled.exr",
                "depthRefined": "{nodeCacheFolder}/<VIEW_ID>_depthMap_refinedFused.exr"
            }
        },
        "FeatureExtraction_1": {
            "nodeType": "FeatureExtraction",
            "position": [
                600,
                0
            ],
            "parallelization": {
                "blockSize": 40,
                "size": 0,
                "split": 0
            },
            "uid": "49bd0fd74f9558a49761e9f8fc50033313b7dd73",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{ImageSegmentationBox_1.input}",
                "masksFolder": "{ImageSegmentationBox_1.output}",
                "maskExtension": "png",
                "maskInvert": false,
                "describerTypes": [
                    "dspsift"
                ],
                "describerPreset": "normal",
                "maxNbFeatures": 0,
                "describerQuality": "normal",
                "contrastFiltering": "GridSort",
                "relativePeakThreshold": 0.01,
                "gridFiltering": true,
                "workingColorSpace": "sRGB",
                "forceCpuExtraction": true,
                "maxThreads": 0,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}"
            }
        },
        "FeatureMatching_1": {
            "nodeType": "FeatureMatching",
            "position": [
                1000,
                0
            ],
            "parallelization": {
                "blockSize": 20,
                "size": 0,
                "split": 0
            },
            "uid": "fa2f03a115c9e5ee57d0576a079c3e3ed24862ba",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{ImageMatching_1.input}",
                "featuresFolders": "{ImageMatching_1.featuresFolders}",
                "imagePairsList": "{ImageMatching_1.output}",
                "describerTypes": "{FeatureExtraction_1.describerTypes}",
                "photometricMatchingMethod": "ANN_L2",
                "geometricEstimator": "acransac",
                "geometricFilterType": "fundamental_matrix",
                "distanceRatio": 0.8,
                "maxIteration": 50000,
                "geometricError": 0.0,
                "knownPosesGeometricErrorMax": 5.0,
                "minRequired2DMotion": 3.0,
                "maxMatches": 0,
                "savePutativeMatches": false,
                "crossMatching": false,
                "guidedMatching": false,
                "matchFromKnownCameraPoses": false,
                "exportDebugFiles": false,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}"
            }
        },
        "ImageDetectionPrompt_1": {
            "nodeType": "ImageDetectionPrompt",
            "position": [
                200,
                0
            ],
            "parallelization": {
                "blockSize": 50,
                "size": 0,
                "split": 0
            },
            "uid": "b016ca3b1440ac4c22bb045de672bc920ac1fd70",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{CameraInit_1.output}",
                "recognitionModelPath": "${RDS_RECOGNITION_MODEL_PATH}",
                "detectionModelPath": "${RDS_DETECTION_MODEL_PATH}",
                "detectionConfigPath": "${RDS_DETECTION_CONFIG_PATH}",
                "prompt": "object",
                "synonyms": "subject, item, main",
                "forceDetection": true,
                "thresholdDetection": 0.4,
                "bboxMargin": 10,
                "useGpu": true,
                "outputBboxImage": false,
                "keepFilename": false,
                "extension": "jpg",
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": "#575963"
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "bboxes": "{nodeCacheFolder}/<VIEW_ID>.jpg"
            }
        },
        "ImageMatching_1": {
            "nodeType": "ImageMatching",
            "position": [
                800,
                0
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 0,
                "split": 1
            },
            "uid": "11d05a034b2fdc7c7faacdffc886a5c5322d0928",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{FeatureExtraction_1.input}",
                "featuresFolders": [
                    "{FeatureExtraction_1.output}"
                ],
                "method": "SequentialAndVocabularyTree",
                "tree": "${ALICEVISION_VOCTREE}",
                "weights": "",
                "minNbImages": 200,
                "maxDescriptors": 500,
                "nbMatches": 40,
                "nbNeighbors": 5,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}/imageMatches.txt"
            }
        },
        "ImageSegmentationBox_1": {
            "nodeType": "ImageSegmentationBox",
            "position": [
                400,
                0
            ],
            "parallelization": {
                "blockSize": 50,
                "size": 0,
                "split": 0
            },
            "uid": "756d44f1b626f8226afaacfc74795f243d286aa7",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{ImageDetectionPrompt_1.input}",
                "bboxFolder": "{ImageDetectionPrompt_1.output}",
                "nukeTracker": "",
                "segmentationModelPath": "${RDS_SEGMENTATION_MODEL_PATH}",
                "maskInvert": false,
                "useGpu": true,
                "keepFilename": true,
                "extension": "png",
                "outputBboxImage": false,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": "#575963"
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "masks": "{nodeCacheFolder}/<FILESTEM>.png",
                "bboxes": "{nodeCacheFolder}/bboxes_<FILESTEM>.jpg"
            }
        },
        "MeshDecimate_1": {
            "nodeType": "MeshDecimate",
            "position": [
                2311.0,
                324.75
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 1,
                "split": 1
            },
            "uid": "3d50c55ef99f37165c0054525dd5e95a0d643b19",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{MeshFiltering_1.outputMesh}",
                "simplificationFactor": 0.05,
                "nbVertices": 0,
                "minVertices": 0,
                "maxVertices": 50000,
                "flipNormals": false,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}/mesh.obj"
            }
        },
        "MeshFiltering_1": {
            "nodeType": "MeshFiltering",
            "position": [
                2202.0,
                4.0
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 1,
                "split": 1
            },
            "uid": "f39dd6717e7f8e363a47c8503e46f16b6e0e468d",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "inputMesh": "{Meshing_1.outputMesh}",
                "outputMeshFileType": "obj",
                "keepLargestMeshOnly": true,
                "smoothingSubset": "all",
                "smoothingBoundariesNeighbours": 0,
                "smoothingIterations": 2,
                "smoothingLambda": 1.0,
                "filteringSubset": "all",
                "filteringIterations": 1,
                "filterLargeTrianglesFactor": 30.0,
                "filterTrianglesRatio": 0.0,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "outputMesh": "{nodeCacheFolder}/mesh.{outputMeshFileTypeValue}"
            }
        },
        "MeshFiltering_2": {
            "nodeType": "MeshFiltering",
            "position": [
                2516.0,
                385.25
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 1,
                "split": 1
            },
            "uid": "2e41584ae463e7710f20297de248e46111467f6f",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "inputMesh": "{MeshDecimate_1.output}",
                "outputMeshFileType": "obj",
                "keepLargestMeshOnly": true,
                "smoothingSubset": "all",
                "smoothingBoundariesNeighbours": 0,
                "smoothingIterations": 2,
                "smoothingLambda": 1.0,
                "filteringSubset": "all",
                "filteringIterations": 1,
                "filterLargeTrianglesFactor": 30.0,
                "filterTrianglesRatio": 0.0,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "outputMesh": "{nodeCacheFolder}/mesh.{outputMeshFileTypeValue}"
            }
        },
        "Meshing_1": {
            "nodeType": "Meshing",
            "position": [
                2000,
                0
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 1,
                "split": 1
            },
            "uid": "2ec67e8f91e9fe55c71ebaeda72c0a9c8f8a6485",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{DepthMapFilter_1.input}",
                "depthMapsFolder": "{DepthMapFilter_1.output}",
                "outputMeshFileType": "obj",
                "useBoundingBox": false,
                "boundingBox": {
                    "bboxTranslation": {
                        "x": 0.0,
                        "y": 0.0,
                        "z": 0.0
                    },
                    "bboxRotation": {
                        "x": 0.0,
                        "y": 0.0,
                        "z": 0.0
                    },
                    "bboxScale": {
                        "x": 1.0,
                        "y": 1.0,
                        "z": 1.0
                    }
                },
                "estimateSpaceFromSfM": true,
                "estimateSpaceMinObservations": 3,
                "estimateSpaceMinObservationAngle": 10.0,
                "maxInputPoints": 50000000,
                "maxPoints": 5000000,
                "maxPointsPerVoxel": 1000000,
                "minStep": 2,
                "partitioning": "singleBlock",
                "repartition": "multiResolution",
                "angleFactor": 15.0,
                "simFactor": 15.0,
                "minVis": 2,
                "pixSizeMarginInitCoef": 2.0,
                "pixSizeMarginFinalCoef": 4.0,
                "voteMarginFactor": 4.0,
                "contributeMarginFactor": 2.0,
                "simGaussianSizeInit": 10.0,
                "simGaussianSize": 10.0,
                "minAngleThreshold": 1.0,
                "refineFuse": true,
                "helperPointsGridSize": 10,
                "densify": false,
                "densifyNbFront": 1,
                "densifyNbBack": 1,
                "densifyScale": 20.0,
                "nPixelSizeBehind": 4.0,
                "fullWeight": 1.0,
                "voteFilteringForWeaklySupportedSurfaces": true,
                "addLandmarksToTheDensePointCloud": false,
                "invertTetrahedronBasedOnNeighborsNbIterations": 10,
                "minSolidAngleRatio": 0.2,
                "nbSolidAngleFilteringIterations": 2,
                "colorizeOutput": false,
                "addMaskHelperPoints": false,
                "maskHelperPointsWeight": 1.0,
                "maskBorderSize": 4,
                "maxNbConnectedHelperPoints": 50,
                "saveRawDensePointCloud": false,
                "exportDebugTetrahedralization": false,
                "seed": 0,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "outputMesh": "{nodeCacheFolder}/mesh.{outputMeshFileTypeValue}",
                "output": "{nodeCacheFolder}/densePointCloud.abc"
            }
        },
        "PrepareDenseScene_1": {
            "nodeType": "PrepareDenseScene",
            "position": [
                1400,
                0
            ],
            "parallelization": {
                "blockSize": 40,
                "size": 0,
                "split": 0
            },
            "uid": "a301e0bd813da6183ce2137cac899848aa20cf75",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{StructureFromMotion_1.output}",
                "imagesFolders": [],
                "masksFolders": [
                    "{ImageSegmentationBox_1.output}"
                ],
                "maskExtension": "png",
                "outputFileType": "exr",
                "saveMetadata": true,
                "saveMatricesTxtFiles": false,
                "evCorrection": false,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "undistorted": "{nodeCacheFolder}/<VIEW_ID>.{outputFileTypeValue}"
            }
        },
        "StructureFromMotion_1": {
            "nodeType": "StructureFromMotion",
            "position": [
                1200,
                0
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 0,
                "split": 1
            },
            "uid": "ac47b3f681b483d8ad72d3bdc04558fc2653384c",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{FeatureMatching_1.input}",
                "featuresFolders": "{FeatureMatching_1.featuresFolders}",
                "matchesFolders": [
                    "{FeatureMatching_1.output}"
                ],
                "describerTypes": "{FeatureMatching_1.describerTypes}",
                "localizerEstimator": "acransac",
                "observationConstraint": "Scale",
                "localizerEstimatorMaxIterations": 50000,
                "localizerEstimatorError": 0.0,
                "lockScenePreviouslyReconstructed": false,
                "useLocalBA": true,
                "localBAGraphDistance": 1,
                "nbFirstUnstableCameras": 30,
                "maxImagesPerGroup": 30,
                "bundleAdjustmentMaxOutliers": 50,
                "maxNumberOfMatches": 0,
                "minNumberOfMatches": 0,
                "minInputTrackLength": 2,
                "minNumberOfObservationsForTriangulation": 2,
                "minAngleForTriangulation": 3.0,
                "minAngleForLandmark": 2.0,
                "maxReprojectionError": 4.0,
                "minAngleInitialPair": 5.0,
                "maxAngleInitialPair": 40.0,
                "useOnlyMatchesFromInputFolder": false,
                "useRigConstraint": true,
                "rigMinNbCamerasForCalibration": 20,
                "lockAllIntrinsics": false,
                "minNbCamerasToRefinePrincipalPoint": 3,
                "filterTrackForks": false,
                "computeStructureColor": true,
                "useAutoTransform": true,
                "initialPairA": "",
                "initialPairB": "",
                "interFileExtension": ".abc",
                "logIntermediateSteps": false,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}/sfm.abc",
                "outputViewsAndPoses": "{nodeCacheFolder}/cameras.sfm",
                "extraInfoFolder": "{nodeCacheFolder}"
            }
        },
        "Texturing_1": {
            "nodeType": "Texturing",
            "position": [
                2400,
                0
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 1,
                "split": 1
            },
            "uid": "c8ee842af91cab2070322f969539c0e4dbbf15c8",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{Meshing_1.output}",
                "imagesFolder": "{DepthMap_1.imagesFolder}",
                "normalsFolder": "",
                "inputMesh": "{MeshFiltering_1.outputMesh}",
                "inputRefMesh": "",
                "textureSide": 4096,
                "downscale": 1,
                "outputMeshFileType": "obj",
                "colorMapping": {
                    "enable": true,
                    "colorMappingFileType": "png"
                },
                "bumpMapping": {
                    "enable": false,
                    "bumpType": "Normal",
                    "normalFileType": "exr",
                    "heightFileType": "exr"
                },
                "displacementMapping": {
                    "enable": false,
                    "displacementMappingFileType": "exr"
                },
                "unwrapMethod": "Basic",
                "useUDIM": false,
                "fillHoles": false,
                "padding": 5,
                "multiBandDownscale": 4,
                "multiBandNbContrib": {
                    "high": 1,
                    "midHigh": 5,
                    "midLow": 10,
                    "low": 0
                },
                "useScore": true,
                "bestScoreThreshold": 0.1,
                "angleHardThreshold": 90.0,
                "workingColorSpace": "sRGB",
                "outputColorSpace": "AUTO",
                "correctEV": true,
                "forceVisibleByAllVertices": false,
                "flipNormals": false,
                "visibilityRemappingMethod": "PullPush",
                "subdivisionTargetRatio": 0.8,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "outputMesh": "{nodeCacheFolder}/texturedMesh.{outputMeshFileTypeValue}",
                "outputMaterial": "{nodeCacheFolder}/texturedMesh.mtl",
                "outputTextures": "{nodeCacheFolder}/texture_*.png"
            }
        },
        "Texturing_2": {
            "nodeType": "Texturing",
            "position": [
                2723.0,
                274.75
            ],
            "parallelization": {
                "blockSize": 0,
                "size": 1,
                "split": 1
            },
            "uid": "73bb49a6e138e0dd418becdd2855405a0a0023b7",
            "internalFolder": "{cache}/{nodeType}/{uid}",
            "inputs": {
                "input": "{Meshing_1.output}",
                "imagesFolder": "{DepthMap_1.imagesFolder}",
                "normalsFolder": "",
                "inputMesh": "{MeshFiltering_2.outputMesh}",
                "inputRefMesh": "",
                "textureSide": 2048,
                "downscale": 2,
                "outputMeshFileType": "obj",
                "colorMapping": {
                    "enable": true,
                    "colorMappingFileType": "jpg"
                },
                "bumpMapping": {
                    "enable": false,
                    "bumpType": "Normal",
                    "normalFileType": "exr",
                    "heightFileType": "exr"
                },
                "displacementMapping": {
                    "enable": false,
                    "displacementMappingFileType": "exr"
                },
                "unwrapMethod": "Basic",
                "useUDIM": false,
                "fillHoles": false,
                "padding": 5,
                "multiBandDownscale": 4,
                "multiBandNbContrib": {
                    "high": 1,
                    "midHigh": 5,
                    "midLow": 10,
                    "low": 0
                },
                "useScore": true,
                "bestScoreThreshold": 0.1,
                "angleHardThreshold": 90.0,
                "workingColorSpace": "sRGB",
                "outputColorSpace": "AUTO",
                "correctEV": true,
                "forceVisibleByAllVertices": false,
                "flipNormals": false,
                "visibilityRemappingMethod": "PullPush",
                "subdivisionTargetRatio": 0.8,
                "verboseLevel": "info"
            },
            "internalInputs": {
                "invalidation": "",
                "comment": "",
                "label": "",
                "color": ""
            },
            "outputs": {
                "output": "{nodeCacheFolder}",
                "outputMesh": "{nodeCacheFolder}/texturedMesh.{outputMeshFileTypeValue}",
                "outputMaterial": "{nodeCacheFolder}/texturedMesh.mtl",
                "outputTextures": "{nodeCacheFolder}/texture_*.jpg"
            }
        }
    }
}