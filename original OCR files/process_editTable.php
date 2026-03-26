<?php


include '../functions/convertJsonToExcel.php';
include '../functions/configFunctions.php';
session_start();

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    
    // Access the shop and supplier name 
    $shop = isset($_POST['shop']) ? $_POST['shop'] : null;
    $supplier = isset($_POST['supplier']) ? $_POST['supplier'] : null;

    //store the $shop and $supplier data in the session 
    $_SESSION['shop'] = $shop;
    $_SESSION['supplier'] = $supplier;


    //upload shop data and supplier data 
    $shopsjsonData = uploadJSONdata('../shops.json');
    $shopData = getShopForm($shopsjsonData,$shop);
    $supplierJsonData = uploadJSONdata('../suppliers.json');

    //get the config relative path 
    $uploadRelativePath = $shopsjsonData['upload_relative_path'];
    $downloadRelativePath = $shopsjsonData['download_relative_path']; 
    $ocrDirRelativePath = $shopsjsonData['ocr_dir_relative_path']; 

    //get the oldest pair in the ocrDirectory (without the suffix)
    $ocrFileName = getOldestPairName("../".$ocrDirRelativePath);

    // Display the file names that was chosen 
    echo "<h1>The file name is: $ocrFileName</h1>";
    
    //build the file path
    $downloadfilePath = "../$downloadRelativePath/$ocrFileName.JSON";
    $ocdFilePathJSON = "../$ocrDirRelativePath/$ocrFileName.JSON";
    $ocdFilePathpdf = "../$ocrDirRelativePath/$ocrFileName.pdf";

    //create the spreadsheet withthe JSON values to OCRsanity format 
    $OCRSanitySpreadsheet = getGENERALJsonInvocieAttributes($ocdFilePathJSON); 

    $supplierName = $OCRSanitySpreadsheet->getActiveSheet()->getCell('B2')->getvalue();

    //upload supplier data
    $supplierData = getSupplierData($supplierJsonData, $supplierName);


    //upload the suplier config object 
    $OCRcheckSumMethod =  $supplierData['OCRsanityMethod'];
    echo "The OCRcheckSumMethod for $supplierName is $OCRcheckSumMethod<br>";

    $sumPair = [0,0];


    //echo for the sum sanity
    echo "Start CheckSum <br>";

    if ($OCRcheckSumMethod == 'Discount2') {
            //if has Discount2 use the checkSumOCRsanityDiscount2 function:
            //check for each line if LineTotal==((Price/(1+Discount1/100))/(1+Discount2/100))*Qty
            // AND if invocie total = calculated total
            $sumPair = checkSumOCRsanityDiscount2($OCRSanitySpreadsheet);
    } elseif ($OCRcheckSumMethod == 'Discount1') {
            //if has Discount1 use the checkSumOCRsanityDiscount1 function:
            //check for each line if LineTotal==(Price*(1-Discount1/100))*Qty
            // AND if invocie total = calculated total
            $sumPair = checkSumOCRsanityDiscount1($OCRSanitySpreadsheet);
    } elseif ($OCRcheckSumMethod == 'LineTotal') {
            //if has LineTotal use the checkSumOCRsanityLineTotal function:
            //check for each line  Linetotal=Price*Qty AND if invocie total = calculated total (sum of all LineTotals)
            $sumPair = checkSumOCRsanityLineTotal($OCRSanitySpreadsheet);
    } elseif ($OCRcheckSumMethod == 'FlatDiscountAndSV') { 
            //if has FlatDiscountNexception use the checkSumOCRsanityNoLineTotal function
            //do a flat discount over the products which are not unders supersision
            $sumPair = checkSumOCRsanityNoLineTotal($OCRSanitySpreadsheet,$shopData);
    } elseif ($OCRcheckSumMethod == 'Simple') {
            //else use the checkSumOCRsanitySimple function
            //check ONLY invocie total = calculated total
            $sumPair = checkSumOCRsanitySimple($OCRSanitySpreadsheet);
    } else {
            //if the method not found by the suppiler name 
            echo "The CheckSum method for the supplier $supplierName was not found";
    }

    
    //check the sanity of the digits on the CatalogNo value
    $OCRSanitySpreadsheet = checkBarcodeSanity($OCRSanitySpreadsheet);

    //save the Spreachsheet to Xlsx file with OCRsanity format 
    $hrefdownloadPath = saveSpreadsheetWithTimestamp($OCRSanitySpreadsheet, $downloadfilePath,$rightToLeft=false,$suffix='_OCRsanity');
    
    //get OCR files to session parameters for future deletion 
    $_SESSION['ocrFileBaseName'] = $ocrFileName;

    //extracting the sums of the invice and calculation 
    $invsum = $sumPair[0]; 
    $calcsum = $sumPair[1];
    //get the sums to session variable
    $_SESSION['invsum'] = $invsum;
    $_SESSION['calcsum'] = $calcsum;

    //get the supplier param and set the LineTotalNotMatch to "true" if the supplierparam[2] = 1 e.g. price = linetotal/Qt
    $supplierParam = $shopData['supplierParam'];
    $supplierElement = null;
    foreach ($supplierParam as $item) {
        if (isset($item[$supplierName])) {
                $supplierElement= $item[$supplierName][2]; // Access the third element (index 2)
            break; // Exit loop once "Tempo" is found
        }
    }

    //set the LineTotalNotMatch parameter based on supplier parameter 
    $LineTotalNotMatch = "";
    if ($supplierElement == 1) {
        $LineTotalNotMatch = "&LineTotalNotMatch=true";
    }

    echo "Supplier Element of $supplierName is $supplierElement <br>";

    //get URL from shopdata 
    $localhostocrViewRawURL = $shopsjsonData['localhostocrViewURL'];
    $hostAddress = $shopsjsonData['hostAddress'];

    //insert the address to the url 
    $localhostocrViewURL = str_replace("localhost", $hostAddress, $localhostocrViewRawURL);

    $IndexURL = $localhostocrViewURL."?invsum=".$invsum."&calcsum=".$calcsum.$LineTotalNotMatch."&pdf=".$ocdFilePathpdf."&xlsx=".$hrefdownloadPath;


    // JavaScript to open the URL in a new window
    echo '<script type="text/javascript">
    window.open("' . $IndexURL . '", "_blank");
    </script>';

    // Add a small delay to ensure the new window is opened before showing the buttons
    echo '<script type="text/javascript">
    setTimeout(function() {
        document.getElementById("choiceForm").style.display = "block";
    }, 5000); // Adjust the timeout if necessary
    </script>';

    //set a link to the screen to download the file
    //echo '<a href="' . $hrefdownloadPath . '" download>Download OCRsanity file</a>';

        
} else {
    echo "<p>Error: Invalid request.</p>";
}
?>