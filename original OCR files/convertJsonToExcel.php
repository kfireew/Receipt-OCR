<?php
require __DIR__ . '/../vendor/autoload.php';  

include 'checkSumMethods.php';
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Style\NumberFormat;
use PhpOffice\PhpSpreadsheet\Style\Border;
use PhpOffice\PhpSpreadsheet\Cell\DataType;
use PhpOffice\PhpSpreadsheet\Cell\Coordinate;



//Generate OCRsanity from Soluma JSON file 
function getGENERALJsonInvocieAttributes($jsonFilePath) {
    //hard code directory

    //create the spreadsheet
    $spreadsheet = new Spreadsheet();
    $sheet = $spreadsheet->getActiveSheet();

    //get the JSON data 
    $jsonData = file_get_contents($jsonFilePath);
    $data = json_decode($jsonData);

    //set the values of the InvoiceNo, VendorNameS, Date, Total and Remarks

    //set InvoiceNo
    $sheet->getCell([1, 1])->setvalue('InvoiceNo');
    $sheet->getCell([2, 1])->setvalue($data->GDocument->fields[0]->value);

    //set VendorNameS
    $sheet->getCell([1, 2])->setvalue('VendorName');
    $sheet->getCell([2, 2])->setvalue($data->GDocument->fields[2]->value);

    //set Date
    $sheet->getCell([1, 3])->setvalue('Date');
    $sheet->getCell([2, 3])->setvalue($data->GDocument->fields[4]->value);

    //set Total
    $sheet->getCell([1, 4])->setvalue('Total');
    $sheet->getCell([2, 4])->setvalue($data->GDocument->fields[6]->value);

    //Autofit
    $sheet->getColumnDimension('A')->setAutoSize(true);
    $sheet->getColumnDimension('B')->setAutoSize(true);

    //look for the Remark feild and set it 
    $sheet->getCell([1, 5])->setvalue('Remarks');
    foreach ($data->GDocument->fields as $field) {
        if ($field->name == 'Remarks') {
            $sheet->getCell([2, 5])->setvalue($field->value);
            break;
        }
    }



    //set the Price, Quantity and CatalogNo headers
    $sheet->getCell([1, 6])->setvalue('Price');
    $sheet->getCell([2, 6])->setvalue('Quantity');
    $sheet->getCell([3, 6])->setvalue('CatalogNo');

    //set the Price, Quantity and CatalogNo, LineTotal and Discount1 and Discount2 headers to BOLD
    $sheet->getStyle('A6:F6')->getFont()->setBold(true);

    //get the CheckSum method based on the supplier configuration 
    $supplierName = $data->GDocument->fields[2]->value;
    $CheckSumMethod = getSupplierOCRcheckSumMethod($supplierName);

    $row = 7; // Start from row 7

    //check if the file have discount2 column
    if ($CheckSumMethod == 'Discount2') {

        //echo for 6-columns OCRsanity
        echo "OCRsanity with 6-columns (include 'Discount1' and 'Discount2' fields)<br>";
        //add the Line Toal header
        $sheet->getCell([4, 6])->setvalue('LineTotal');
        //add the Discount1 header
        $sheet->getCell([5, 6])->setvalue('Discount1');
        //add the Discount2 header
        $sheet->getCell([6, 6])->setvalue('Discount2');

        foreach ($data->GDocument->fields as $field) {
            // Check the field name and update the current field type
            if ($field->name == 'Price') {
                //set the price value 
                $sheet->getCell([1, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([1,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([1,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'Quantity') {
                //set the Quantity value 
                $sheet->getCell([2, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([2,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([2,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'CatalogNo') {
                //set the CatalogNo value and format
                $sheet->getCell([3, $row])->setvalue($field->value);
                $sheet->setCellValueExplicit([3, $row], $field->value, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
                
            } elseif ($field->name == 'LineTotal') {
                //set the LineToal value 
                $sheet->getCell([4, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([4,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([4,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
                
            } elseif ($field->name == 'Discount1') {
                //set the Quantity value 
                $sheet->getCell([5, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([5,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([5,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'Discount2') {
                //set the Quantity value 
                $sheet->getCell([6, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([6,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([6,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }

                //Discount2 is last in the sequence - jump one row down
                $row++;
    
            } else {
                //if not one of these names then continue 
                continue;
            }

        }
       //if the the checksum method is Discount1 
    } elseif ($CheckSumMethod == 'Discount1') {

        //echo for 6-columns OCRsanity
        echo "OCRsanity with 5-columns (include 'Discount1' field)<br>";
        //add the Line Toal header
        $sheet->getCell([4, 6])->setvalue('LineTotal');
        //add the Discount1 header
        $sheet->getCell([5, 6])->setvalue('Discount1');
        //add the Discount2 header
        //$sheet->getCell([6, 6])->setvalue('Discount2');

        foreach ($data->GDocument->fields as $field) {
            // Check the field name and update the current field type
            if ($field->name == 'Price') {
                //set the price value 
                $sheet->getCell([1, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([1,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([1,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'Quantity') {
                //set the Quantity value 
                $sheet->getCell([2, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([2,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([2,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'CatalogNo') {
                //set the CatalogNo value and format
                $sheet->getCell([3, $row])->setvalue($field->value);
                $sheet->setCellValueExplicit([3, $row], $field->value, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
                
            } elseif ($field->name == 'LineTotal') {
                //set the LineToal value 
                $sheet->getCell([4, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([4,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([4,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
                
            } elseif ($field->name == 'Discount1') {
                //set the Quantity value 
                $sheet->getCell([5, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([5,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([5,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }

                //Discount1 is last in the sequence - jump one row down
                $row++;
    
            } /*elseif ($field->name == 'Discount2') {
                //set the Quantity value 
                $sheet->getCell([6, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([6,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([6,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }

                //Discount2 is last in the sequence - jump one row down
                $row++;
    
            }*/ else {
                //if not one of these names then continue 
                continue;
            }

        }
    //check if the file  LineToal column 
    } elseif ($CheckSumMethod == 'LineTotal') {

        //echo for 4-columns OCRsanity
        echo "OCRsanity with 4-columns (include 'Line Total' field)<br>";
        //add the Line Toal header
        $sheet->getCell([4, 6])->setvalue('LineTotal');

        foreach ($data->GDocument->fields as $field) {
            // Check the field name and update the current field type
            if ($field->name == 'Price') {
                //set the price value 
                $sheet->getCell([1, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([1,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([1,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'Quantity') {
                //set the Quantity value 
                $sheet->getCell([2, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([2,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([2,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'CatalogNo') {
                //set the CatalogNo value and format
                $sheet->getCell([3, $row])->setvalue($field->value);
                $sheet->setCellValueExplicit([3, $row], $field->value, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
                
            } elseif ($field->name == 'LineTotal') {
                //set the LineToal value 
                $sheet->getCell([4, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([4,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([4,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
                //jump one row down
                $row++;
                
            }else {
                //if not one of these names then continue 
                continue;
            }

        }
    
    } elseif ($CheckSumMethod == 'Simple' or $CheckSumMethod == 'FlatDiscountAndSV') {
    
        //echo for 3-Columns OCRsanity
        echo "OCRsanity with 3-Columns <br>";

        foreach ($data->GDocument->fields as $field) {
            // Check the field name and update the current field type
            if ($field->name == 'Price') {
                //set the price value 
                $sheet->getCell([1, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([1,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([1,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'Quantity') {
                //set the Quantity value 
                $sheet->getCell([2, $row])->setvalue($field->value);
                //if the value is not numeric - paint the cell in purple
                if (!is_numeric($field->value)) {
                    $sheet->getStyle([2,$row])->getFill()->setFillType(Fill::FILL_SOLID);
                    $sheet->getStyle([2,$row])->getFill()->getStartColor()->setARGB('80DCC8FF'); 
                }
    
            } elseif ($field->name == 'CatalogNo') {
                //set the Quantity value and format
                $sheet->getCell([3, $row])->setvalue($field->value);
                // Apply number format with zero decimal places
                $sheet->setCellValueExplicit([3, $row], $field->value, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
                //jump one row down
                $row++;
                
            } else {
                //if not one of these names then continue 
                continue;
            }

        }
    
    } else {
        //no checksum method was found 
        echo "No CheckSum method was implemented<br>";
    }

    //Autofit Column C (CatalogNo)
    $sheet->getColumnDimension('C')->setAutoSize(true);

    return $spreadsheet;
}


//Generate Comax format from OCR sanity file 
function convertToPriceListBasicSheet($OCRsanitySpreadSheet, $shopData) {


    // Extract column values of "Price", "Quantity", "CatalogNo", "Diff", and "OriginalPrice" for Comax format
    $SSPriceCl = $SSquantityCl = $SScatalogNoCl = $SSdiffCl = $SSoriginalPriceCl = null;
    foreach ($shopData['attributesColumns'] as $column) {
    if (isset($column['Price'])) {
            $SSPriceCl = (int)$column['Price'];
        } elseif (isset($column['Quantity'])) {
            $SSquantityCl = (int)$column['Quantity'];
        } elseif (isset($column['CatalogNo'])) {
            $SScatalogNoCl = (int)$column['CatalogNo'];
        } 
    }

    //echo "SS Price: $SSPriceCl, SS Quantity: $SSquantityCl, SS CatalogNo: $SScatalogNoCl <br>";


    // Load the OCR sanity file using PhpSpreadsheet
    $OCRsheet = $OCRsanitySpreadSheet->getActiveSheet();

    //Create a new sheet for the Comax spreadsheet 
    $PriceListBasicspreadsheet = new Spreadsheet();
    $PLbasicSheet = $PriceListBasicspreadsheet->getActiveSheet();

    //Get the headers from the confige file 
    $headerArray = $shopData['headers'];

    //echo "Headers are: ".implode(', ', $headerArray);

    // Get the size of the header array 
    $headerArryZise = sizeof($headerArray);

    // Iterate through the headers array 
    for ($columnIndex = 1; $columnIndex <= $headerArryZise; $columnIndex++) {
        //set the header strings in the columns 
        $PLbasicSheet->getCell([$columnIndex,1])->setvalue($headerArray[$columnIndex-1]);
    }

    // Iterate through the OCRsanity file from line 7 and onward and copy 
    //the values of Price, Quantity and CatalogNo to the corspondant location in the Comax file


    //the $PriceVal, (e.g. the price of the product), can be:
    //0 -  the price in the invoice that was read by the OCR
    //1 - the LineToal devided to the Qty - this will give the price without diff from total 

    //get supplier name from the config file 
    $supplierName = $OCRsheet->getCell([2,2])->getvalue();
    //get price param e.g. - do we take the price from the price colums in OCSsanity (priceParam = 0) or
    //or we divid the linetotal by the quantity of the products to avoid differences 
    $priceParam = getSupplierPriceParam($shopData,$supplierName);


    //get the last row 
    $lastUsedRow = $OCRsheet->getHighestRow('A');

    for ($rowIndex = 7; $rowIndex <= $lastUsedRow; $rowIndex++) {

        //set line number 
        $PLbasicSheet->getCell([1,$rowIndex-5])->setvalue($rowIndex-6);

        //set Quantity value
        $quantityVal = $OCRsheet->getCell([2,$rowIndex])->getvalue();
        $PLbasicSheet->getCell([$SSquantityCl,$rowIndex-5])->setvalue($quantityVal);

        //set price value
        if ($priceParam ==0) {
            //price will be taken from the price colums in OCSsanity 
            $priceVal = $OCRsheet->getCell([1,$rowIndex])->getvalue();
        } elseif ($priceParam ==1) {
            //price will be the division of LineToal and Qty 
            $LineToalVal = $OCRsheet->getCell([4,$rowIndex])->getvalue();
            //get the unless $priceVal = $LineToalVal/$quantityVal;
            if ($quantityVal != 0) {
                $priceVal = $LineToalVal/$quantityVal; //round to 2 digist  - round($LineToalVal/$quantityVal,2)
            } else {
                $actualRow = ($rowIndex-7);
                echo "Quantity is zero so price will be zero in line $actualRow <br>";
            }

        } else {
            //in case no value for price param was found 
            echo "No price Param value was found <br>";
        }
        
        $PLbasicSheet->getCell([$SSPriceCl,$rowIndex-5])->setvalue($priceVal);

        //set CatalogNo value
        $catalogNoVal = $OCRsheet->getCell([3,$rowIndex])->getvalue();
        $PLbasicSheet->getCell([$SScatalogNoCl,$rowIndex-5])->setvalue($catalogNoVal);
        //format the catalogNo as a string 
        $PLbasicSheet->setCellValueExplicit([$SScatalogNoCl,$rowIndex-5], $catalogNoVal, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
    }

    //Autofit Column B (CatalogNo)
    $PLbasicSheet->getColumnDimension('B')->setAutoSize(true);

    return $PriceListBasicspreadsheet;

}


function processPriceListcheck($itemsSpreasdsheet,$shopData,$PriceListFile) { 


    // Extract column values of "Price", "Quantity", "CatalogNo", "Diff", "OriginalPrice" , "ItemName" and "Department"
    $SSPriceCl = $SSsalesPriceCl = $SScatalogNoCl = $SSdiffCl = $SSoriginalPriceCl = $SSitemNameCl = $SSDepartmentCl = null;
    foreach ($shopData['attributesColumns'] as $column) {
    if (isset($column['Price'])) {
            $SSPriceCl = (int)$column['Price'];
        } elseif (isset($column['Quantity'])) {
            $SSquantityCl = (int)$column['Quantity'];
        } elseif (isset($column['CatalogNo'])) {
            $SScatalogNoCl = (int)$column['CatalogNo'];
        } elseif (isset($column['Diff'])) {
            $SSdiffCl = (int)$column['Diff'];
        } elseif (isset($column['OriginalPrice'])) {
            $SSoriginalPriceCl = (int)$column['OriginalPrice'];
        } elseif (isset($column['SalePrice'])) {
            $SSsalesPriceCl = (int)$column['SalePrice'];
        } elseif (isset($column['ItemName'])) {
            $SSitemNameCl = (int)$column['ItemName'];
        } elseif (isset($column['Department'])) {
            $SSDepartmentCl = (int)$column['Department'];
        }
    }

    
    // Extract column values of "CatalogNo" "Price", "Sales Price", "Name" and "Department" from pricelist 
    $PLPriceCl = $PLcatalogNoCl = $PLsalePriceCl = $PLitemNameCl = $PLDepartmentCl = null;
    foreach ($shopData['priceListColumns'] as $column) {
    if (isset($column['Price'])) {
            $PLPriceCl = (int)$column['Price'];
        } elseif (isset($column['CatalogNo'])) {
            $PLcatalogNoCl = (int)$column['CatalogNo'];
        } elseif (isset($column['SalePrice'])) {
            $PLsalePriceCl = (int)$column['SalePrice'];
        } elseif (isset($column['ItemName'])) {
            $PLitemNameCl = (int)$column['ItemName'];
        } elseif (isset($column['Department'])) {
            $PLDepartmentCl = (int)$column['Department'];
        }
    } 


    // Load the priceList file using PhpSpreadsheet
    $priceListSpreadsheet = \PhpOffice\PhpSpreadsheet\IOFactory::load($PriceListFile);
    $priceListSheet = $priceListSpreadsheet->getActiveSheet();
    $priceListData = [];

    //get the comax sheet from spreadsheet 
    $itemsSheet = $itemsSpreasdsheet->getActiveSheet();

    
    // Iterate through rows (starting from row 2) to create associative arry for pricelist
    foreach ($priceListSheet->getRowIterator(2) as $row) {

        $PLcatalogNoVal = $priceListSheet->getCell([$PLcatalogNoCl, $row->getRowIndex()])->getValue();
        $PLpriceVal = $priceListSheet->getCell([$PLPriceCl, $row->getRowIndex()])->getValue();
        $PLsalePriceVal = $priceListSheet->getCell([$PLsalePriceCl, $row->getRowIndex()])->getValue();
        $PLitemNameVal = $priceListSheet->getCell([$PLitemNameCl, $row->getRowIndex()])->getValue();
        $PLDepartmentVal = $priceListSheet->getCell([$PLDepartmentCl, $row->getRowIndex()])->getValue();

        // Save data in associative array
        $priceListData[] = [
            'CatalogNo' => $PLcatalogNoVal,
            'Price' => $PLpriceVal,
            'SalePrice' => $PLsalePriceVal,
            'ItemName' => $PLitemNameVal,
            'Department' => $PLDepartmentVal,
        ];
    }


    // set the columns index
    $CatalogNocolumnIndex = $SScatalogNoCl; 
    $PricecolumnIndex = $SSPriceCl;
    $DiffColumnIndex = $SSdiffCl;
    $OriginalPricecolumnIndex = $SSoriginalPriceCl;
    $SalePriceColumnIndex = $SSsalesPriceCl;
    $ItemNameColumnIndex =$SSitemNameCl;
    $DepartmentNameColumnIndex =$SSDepartmentCl;

    // Get the highest row number in the active sheet
    $highestRow = $itemsSheet->getHighestRow();

    //in this function version always invoice codes will be replaces by pricelist code 
    $replaceToPriceListCode = true; 


    // Iterate through the CatalogNo cells
    for ($rowIndex = 2; $rowIndex <= $highestRow; $rowIndex++) {
        // Access the CatalogNo and Price values of the item sheet
        $catalogNoVal = $itemsSheet->getCell([$CatalogNocolumnIndex, $rowIndex])->getValue();
        $priceVal = $itemsSheet->getCell([$PricecolumnIndex, $rowIndex])->getValue();

        //if the $priceVal is not numeric then continue to next row
        if (!is_numeric($priceVal)) {
            //echo 
            $trueInvoiceLine = $rowIndex-1;
            echo "Price value for invocie line number $trueInvoiceLine is not numeric <br>";
            //set the Diff cell to be "No Inv price"
            $itemsSheet->getCell([$DiffColumnIndex, $rowIndex])->setvalue('No Inv Price');
            //continue to next row
            continue;

        }

        
        //check if the CatalogNoVal exists in the $priceListData and if so echo it 
        $CatalogNoExistsInPriceList = false; 
        foreach ($priceListData as $index => $item) {

            // Check if $catalogNoVal exists in the 'CatalogNo' key of the array
            if ($item['CatalogNo'] == $catalogNoVal) {
                //echo "Value $catalogNoVal exists in the array at index $index.<br>";
                $CatalogNoExistsInPriceList = true;
                //$CatalogNoItemIndex = $index;
                break;
                // You can also access other information if needed, e.g., $item['Price']
            } 


            $tempcatalogNoVal = $catalogNoVal;

            $tempItemCatalogNo = $item['CatalogNo'];

            //*****fix when $catalogNoVal (number coming from the invoice) have 5 digist only but not the pricelist item */
            if ((strlen($tempItemCatalogNo) > 5) and (strlen($tempcatalogNoVal) == 5)) {
                //add 0 to the left of the number 
                $tempcatalogNoVal = "0".$tempcatalogNoVal;
                //echo "New padded catalogNoVal is $tempcatalogNoVal <br>";
            }

            //$item['CatalogNo'] = PriceList Value
            //$catalogNoVal = Invoice value
            //if the case that the PriceList Value is a shortcode of Invoice value
            // THEN: prompt and insert to the PriceList Value to excel 
            //ESLEIF: Invoice value is a shortcode of PriceList Value 
            //THEN: prompt but keep the Invoice value in the excel
            if (isItemSuffix($tempItemCatalogNo, $tempcatalogNoVal, 5)) { //$catalogNoVal, 5

                $CatalogNoExistsInPriceList = true;
                $invoiceItem = $catalogNoVal;
                $pricelistItem = $item['CatalogNo'];
                
                echo "PriceList item $pricelistItem is a shortcode of $invoiceItem  in the invoice<br>";

                //replace the long code of the invoice to the shortcode of the pricelist - this is in case that 
                //the backoffice codes are the shortcodre and the invoice codes are the long ones
                if ($replaceToPriceListCode) {

                    //set the short code in column of the CatalogNo 
                    //$itemsSheet->getCell([$CatalogNocolumnIndex, $rowIndex])->setValue($shortCodeVal);
                    $itemsSheet->setCellValueExplicit([$CatalogNocolumnIndex, $rowIndex], $pricelistItem, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);

                    //echo the replacement 
                    echo "Price list item $pricelistItem was set in excel<br>";

                    //paint the cell in yellow 
                    $itemsSheet->getStyle([$CatalogNocolumnIndex, $rowIndex])->getFill()->setFillType(Fill::FILL_SOLID);
                    $itemsSheet->getStyle([$CatalogNocolumnIndex, $rowIndex])->getFill()->getStartColor()->setARGB('80FFFF00'); 

                } 


                break;

            } elseif (isItemSuffix($tempcatalogNoVal,$tempItemCatalogNo, 5)) { // $item['CatalogNo'], 5
                //check if the invoice value () is a short code of the Price lits value
                //if so it replace it to the pricelist value

                /*
                $CatalogNoExistsInPriceList = true;
                $shortCodeVal = $catalogNoVal;
                $pricelistVal = $item['CatalogNo'];
                
                /cho "Invoice item $shortCodeVal is a shortcode of $pricelistVal in the invoice<br>";

                break; */

                $CatalogNoExistsInPriceList = true;
                $invoiceItem = $catalogNoVal;
                $pricelistItem = $item['CatalogNo'];
                
                echo "Invoice item $invoiceItem is a shortcode of price list item $pricelistItem<br>";

                //replace the long code of the invoice to the shortcode of the pricelist - this is in case that 
                //the backoffice codes are the shortcodre and the invoice codes are the long ones
                if ($replaceToPriceListCode) {

                    //set the short code in column of the CatalogNo 
                    //$itemsSheet->getCell([$CatalogNocolumnIndex, $rowIndex])->setValue($shortCodeVal);
                    $itemsSheet->setCellValueExplicit([$CatalogNocolumnIndex, $rowIndex], $pricelistItem, \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);

                    //echo the replacement 
                    echo "Price list item $pricelistItem was set in excel<br>";

                    //paint the cell in yellow 
                    $itemsSheet->getStyle([$CatalogNocolumnIndex, $rowIndex])->getFill()->setFillType(Fill::FILL_SOLID);
                    $itemsSheet->getStyle([$CatalogNocolumnIndex, $rowIndex])->getFill()->getStartColor()->setARGB('80FFFF00'); 

                } 

                break;


            }


        }

        //if the CatalogNo exists in the price list then we compare the prices and act accordingly
        
        if ($CatalogNoExistsInPriceList == true) {
            
            //echo "Value $catalogNoVal exists in the array at index $index.<br>";
            //get the price of the item in the $priceListData
            $PLprice = $priceListData[$index]['Price'];
            //get the sales price of the item in the $priceListData
            $PLsalePrice = $priceListData[$index]['SalePrice'];
            //get the item name in the $priceListData
            $PLitemName = $priceListData[$index]['ItemName'];
            //get the department name in the $priceListData
            $PLdepartmentName = $priceListData[$index]['Department'];

            //write the Item name in the Comax sheet 
            $itemsSheet->getCell([$ItemNameColumnIndex, $rowIndex])->setvalue($PLitemName);
            //echo "Item name is $PLitemName <br>";

            //write the Item name in the Comax sheet 
            $itemsSheet->getCell([$DepartmentNameColumnIndex, $rowIndex])->setvalue($PLdepartmentName);
        
            //check if the price exists in the pricelist 
            if (!$PLprice) {
                //if price does not exist in pricelist then write "No Price" at Diff column 
                $itemsSheet->getCell([$DiffColumnIndex, $rowIndex])->setvalue('No PL Price');
                //set the $sale price for later margin and sales recommnedation 
                $itemsSheet->getCell([$SalePriceColumnIndex, $rowIndex])->setvalue($PLsalePrice);
            } elseif ($PLprice == round($priceVal,2)) { //OLD version - compare "$PLprice == $priceVal" new version diff in 
                // if the price exists compare the price of pricelist and price value 
                //if the prices are the same. write 0 (zero) in the Diff column 
                $itemsSheet->getCell([$DiffColumnIndex, $rowIndex])->setvalue(0);
            } else {
                //if the prices are different then
                //write the original price in the original price column 
                $itemsSheet->getCell([$OriginalPricecolumnIndex, $rowIndex])->setvalue($PLprice);
                //write the sales price in the sales price column
                $itemsSheet->getCell([$SalePriceColumnIndex, $rowIndex])->setvalue($PLsalePrice);
                //calculate the % diffence and write it in the Diff column 
                $diffPercentage = $priceVal/$PLprice-1;
                $itemsSheet->getCell([$DiffColumnIndex, $rowIndex])->setvalue($diffPercentage);
                //set the % style
                // Get the cell's style
                $style = $itemsSheet->getStyle([$DiffColumnIndex, $rowIndex]);
                // Set the number format to percentage
                $style->getNumberFormat()->setFormatCode(NumberFormat::FORMAT_PERCENTAGE_00);

                //if the price increased ($diffPercentage>0) then paint the cell background in red 
                $itemsSheet->getStyle([$DiffColumnIndex, $rowIndex])->getFill()->setFillType(Fill::FILL_SOLID);

                if ($diffPercentage>0) {
                    //if the price INCREASE set the cell background as light red
                    $itemsSheet->getStyle([$DiffColumnIndex, $rowIndex])->getFill()->getStartColor()->setARGB('80FFCCCC');
                    
                    //->getFill()->setFillType(Fill::FILL_SOLID)->getStartColor()->setRGB($red, $green, $blue);
                } else {
                    //if the price DECREASE set the cell background as light green
                    $itemsSheet->getStyle([$DiffColumnIndex, $rowIndex])->getFill()->getStartColor()->setARGB('8080FF80'); 

                }
            }


        } else {
            //if the CatalogNo not in pricelist we write "Not Found" in $DiffColumnIndex
            echo "Value $catalogNoVal NOT EXISTS in Price List.<br>";
            $itemsSheet->getCell([$DiffColumnIndex, $rowIndex])->setvalue('Not Found');
            //set the color to light purpule 
            $itemsSheet->getStyle([$CatalogNocolumnIndex, $rowIndex])->getFill()->setFillType(Fill::FILL_SOLID);
            $itemsSheet->getStyle([$CatalogNocolumnIndex, $rowIndex])->getFill()->getStartColor()->setARGB('80DCC8FF');

        }
        
    }

    return $itemsSpreasdsheet;

}

//clean the colors and the frames from an OCRsanity file 
function cleanOCRsanityFile($OCRsanitySpreadSheet) {

    //get the sheet
    $OCRsanitySheet = $OCRsanitySpreadSheet->getActiveSheet();

    //get the last row of the OCRsanity file
    $lastUsedRow = $OCRsanitySheet->getHighestRow('A');

    //define the range
    //$range = 'A7:D'.$lastUsedRow;


   for ($rowIndex = 7; $rowIndex <= $lastUsedRow; $rowIndex++) { 

        for ($columnIndex = 1; $columnIndex <= 4; $columnIndex++) {

            $cell = $OCRsanitySheet->getcell([$columnIndex,$rowIndex]);

            // Reset fill color
            $cell->getStyle()->getFill()->setFillType(\PhpOffice\PhpSpreadsheet\Style\Fill::FILL_NONE);

            // Reset font color
            //$cell->getStyle()->getFont()->getColor()->setARGB(null);

            // Reset borders
            $cell->getStyle()->getBorders()->getAllBorders()->setBorderStyle(Border::BORDER_NONE);

            // Output the cell address
            //$cellCoordinate = $cell->getCoordinate();
            //echo "Cell Address: $cellCoordinate";


        }


   }


    return $OCRsanitySpreadSheet;


}



//check if $item is the suffix of $catalogNoVal (but only if item longer than $minLen)
function isItemSuffix($item, $catalogNoVal, $minLen) {

    //trim spaces in begining and end 
    $item = trim($item);
    $itemLength = strlen($item);

    

    if ($itemLength >= $minLen) {
        $suffixOfCatalogNo = substr($catalogNoVal, -$itemLength);
        //echo "Short code test: suffixItem:$suffixItem item:$item <br>";
        return $suffixOfCatalogNo == $item;
    }

    return false;
}


function creatListOfNewProducts($itemsAfterPriceListcheck,$NOT_FOUNDcolumn,$shopData,$supplier, $originalfileName) {


    //create new products basic list
    $newProductsBasicList = creatListOfNewProductsBasic($itemsAfterPriceListcheck,$NOT_FOUNDcolumn);

    //save the file for debug

    //if the list is empty - return null
    if (!$newProductsBasicList) {

        //echo "No new products in the invoice <br>";
        return null;

    }

    //get the headers array:
    $headersArray = $shopData['newProductsHeaders'];

    //get the mapping array 
    $toNewProductMapping = $shopData['toNewProductMapping'];

    //map the basic spreadsheet to the new spreadsheet 
    $newProductsList  = copyColumnsAndHeadersToNewSpreadsheet($newProductsBasicList, $headersArray, $toNewProductMapping);

    //get the $supplierParam
    $supplierParam = $shopData['supplierParam']; 

    //add the supplier index from the $shopData
    $newProductsList = addSupplier($newProductsList,$supplier,$supplierParam);

    //*************add department number ************
    //get department config data
    $departmentsConfigFileLocation = $shopData['departmentsConfigFile'];
    $departmentConfigObject = uploadJSONdata($departmentsConfigFileLocation);
    $newProductsList = addDepartmentNumber($newProductsList,$departmentConfigObject,$shopData);

    //********* add invocie identifier  */
    //get the invoice identifier from file name 
    $invoiceIdentifier = generateInvoiceIdentifierFromFileName($originalfileName);
    //get the invoice identifier column from config
    $newProductsItemsInducators = $shopData['newProductsItemsInducators'];
    $invoiceIdentifierColumn = $newProductsItemsInducators[2];
    //update the new product sheet with the invoice identifier 
    updateColumnWithSingleValue($newProductsList ,$invoiceIdentifierColumn,$invoiceIdentifier);

    return $newProductsList; 


}

function creatListOfNewProductsBasic($itemsAfterPriceListcheck,$NOT_FOUNDcolumn) {

        //clone a new sheet
        $newProductsSpreadsheet = $itemsAfterPriceListcheck->copy();

        // Get the active sheet
        $sheet = $newProductsSpreadsheet->getActiveSheet();

        // Get the highest row number
        $highestRow = $sheet->getHighestRow();
    
        // Iterate through each row starting from the second row
        for ($row = 2; $row <= $highestRow; $row++) {
            // Check if the value in the specified column of the current row is "Not Found" 
            $NOT_FOUND_columns_value = $sheet->getCell([$NOT_FOUNDcolumn, $row])->getValue();
            if ( $NOT_FOUND_columns_value !== "Not Found") {
                // If it's not "Not Found"  remove the row from the spreadsheet
                $sheet->removeRow($row);
                // Decrement $row as we removed a row
                $row--;
                // Decrement $highestRow as well
                $highestRow--;
            } 

        }

        //if the list is empty return NULL
        $highestRow = $sheet->getHighestRow();
        //echo "Highest Row: $highestRow <br>";
        if ($highestRow==1) {
            //debug:
            //echo "highestRow $highestRow <br>";
            //means no new products 
            //echo "Basic list: No new products in this invoice<br>";
            $newProductsSpreadsheet = null;

        }

        return $newProductsSpreadsheet;

}

//the function get a OCR sanity file and check if the barcodes are numeric (digits)
function checkBarcodeSanity($OCRsanitySpreadSheet) {

    // Get the active sheet
    $sheet = $OCRsanitySpreadSheet->getActiveSheet();

    // Get the highest row and column that contain data
    $highestRow = $sheet->getHighestRow();
    //$highestColumn = $sheet->getHighestColumn();

    // Convert the highest column letter to a column index
    //$highestColumnIndex = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString($highestColumn);

    // Loop through each row starting from row 7 and column C
    for ($row = 7; $row <= $highestRow; $row++) {
        $cellValue = $sheet->getCell([3, $row])->getValue(); // Column C is index 3
        
        // Check if the cell value consists only of digits
        if (!ctype_digit($cellValue)) {
            echo "Barcode $cellValue - Not All characters are digits<br>";
            // Paint the cell in light yellow
            $sheet->getStyle([3, $row])->getFill()->setFillType(\PhpOffice\PhpSpreadsheet\Style\Fill::FILL_SOLID)->getStartColor()->setARGB('60FFFF80');
        } 
        
        //check if the cell value longer than 13 
        if (strlen($cellValue) > 13) {
            echo "Barcode $cellValue longer than 13 characters<br>";
            // Paint the cell in light yellow
            $sheet->getStyle([3, $row])->getFill()->setFillType(\PhpOffice\PhpSpreadsheet\Style\Fill::FILL_SOLID)->getStartColor()->setARGB('60FFFF80');
        }
    }

    // return the modified spreadsheet
    return $OCRsanitySpreadSheet;

}

//get supplier config object by supplier name 
function getSupplierOCRcheckSumMethod($supplierName) {

    // Read the JSON file
    $jsonData = file_get_contents('../suppliers.json');

    // Decode the JSON data into an associative array
    $suppliers = json_decode($jsonData, true);

    $OCRsanityCheckSumMethod = null;

    // Search for the supplier by name
    foreach ($suppliers as $supplier) {
        if ($supplier['supplierName'] == $supplierName) {
            $OCRsanityCheckSumMethod = $supplier['OCRsanityMethod'];
            //echo "The OCRsanityCheckSumMethod for $supplierName is: $OCRsanityCheckSumMethod";
            break; // Exit the loop once the supplier is found
        }
    }

    if (!$OCRsanityCheckSumMethod) {
        echo "Supplier '$supplierName' checkSum method was not found in the config file.<br>";
        $OCRsanityCheckSumMethod = "Supplier Not Found";
    }

    return $OCRsanityCheckSumMethod;
}

//copy specific columns from a spreadsheet to a new spreadhseet and gets new headers base on headers array 
function copyColumnsAndHeadersToNewSpreadsheet($sourceSpreadsheet, $headersArray, $toNewSheetMapping) {
    
    //if $productsBasicList is null return null
    if (!$sourceSpreadsheet) {
        return $sourceSpreadsheet;
    }
    
    // Load the basic and new products spreadsheets
    $newSpreadsheet = new Spreadsheet();
    $newSheet = $newSpreadsheet->getActiveSheet();

    //geting the $BasicList sheet 
    $sourceSheet = $sourceSpreadsheet->getactivesheet();

    // Set headers in the first row of the new products sheet
    $newSheet->fromArray([$headersArray], null, 'A1');

    $lastUsedRow = $sourceSheet->getHighestRow('A');

    // Iterate over each mapping pair and copy columns accordingly
    foreach ($toNewSheetMapping as $mapping) {
        $sourceColumnIndex = $mapping[0];
        $destinationColumnIndex = $mapping[1];
        $type = $mapping[2];

        //iterate through the rows and copy the values 
        for ($rowIndex = 2; $rowIndex <= $lastUsedRow; $rowIndex++) {

            //get the cell value from the source
            $cellVal = $sourceSheet->getCell([$sourceColumnIndex,$rowIndex])->getvalue();
            //echo "Cell value $cellVal";
            if ($type==1) {
                //type 1 = regular copy 
                $newSheet->getCell([$destinationColumnIndex,$rowIndex])->setvalue($cellVal);
            } elseif ($type==2) {
                //type 2 = regular copy 
                $newSheet->setCellValueExplicit([$destinationColumnIndex,$rowIndex], $cellVal, DataType::TYPE_STRING);
            } else {
                //any other type 2 = regular copy 
                echo "Copy type $type not defined <br>";
            }
            
        } 

        //autofit the column 
        $newSheet->getColumnDimensionByColumn($destinationColumnIndex)->setAutoSize(true);
    }

    return $newSpreadsheet;
}

function addSupplier($newProductsList,$supplier,$supplierArray) {

    //get the info about supplier and department columns 
    $supplierObject= $supplierArray[0];
    $supplierRawColumns = $supplierObject["supplierNDepartmentColumns"];
    $supplierColumn = $supplierRawColumns[0]; 
    //$departmentColumn = $supplierNDepartmentColumns[1]; 

    //get the info about supplier index and department defult index 

    //get the supplier item 
    foreach ($supplierArray as $item) {
        if (isset($item[$supplier])) {
            $supplierValues = $item[$supplier];
            break;
        }
    }

    //set defult values 
    $supplierIndexValue = $supplier;
    //$departmentIndexValue = $supplier."DefultDepartment";

    //get the supplier values 
    if (isset($supplierValues)) {
        $supplierIndexValue = $supplierValues[0]; // supplier index as in the back office 
        //$departmentIndexValue = $supplierValues[1]; // defult department index for that supplier  as in the back office 
        //echo "Supplier Index Value : $supplierIndexValue, Department Index Value : $departmentIndexValue <br>";
    } else {
        echo "$supplier key for supplier and defult department index not found  - defult values will be set<br>";
    }

    //itterate through the $newProductsList and set the department index and supplier index
    $sheet = $newProductsList->getActiveSheet();
    $highestRow = $sheet->getHighestRow();

    for ($rowIndex = 2; $rowIndex <= $highestRow; $rowIndex++) {

        //set the values
        if ($supplierColumn > 0) { //if the supplier needed in the file format (the column in th shops.json is not 0)
            $sheet->getCell([$supplierColumn,$rowIndex])->setValue($supplierIndexValue);
        }
        /*if ($departmentColumn > 0) { //if the deprtment needed in the file format (the column in th shops.json is not 0)
            $sheet->getCell([$departmentColumn,$rowIndex])->setValue($departmentIndexValue);
        } */
        
    }

    return $newProductsList;

}



function addDepartmentNumber($newProductsList, $departmentConfigObject, $shopData) {
    // Extract indicators from shopData
    $newProductsItemsIndicators = $shopData["newProductsItemsInducators"];
    $departmentNameColumn = $newProductsItemsIndicators[0]; // Column number for Department Name
    $departmentNumberColumn = $newProductsItemsIndicators[1]; // Column number for Department Number

    // Convert column numbers to letters
    $departmentNameColumnLetter = Coordinate::stringFromColumnIndex($departmentNameColumn);
    $departmentNumberColumnLetter = Coordinate::stringFromColumnIndex($departmentNumberColumn);

    // Get the active worksheet
    $worksheet = $newProductsList->getActiveSheet();
    $highestRow = $worksheet->getHighestRow();

    // Loop through rows starting from row 2
    for ($row = 2; $row <= $highestRow; $row++) {
        // Get the Department Name value from the specified column
        $departmentName = $worksheet->getCell($departmentNameColumnLetter . $row)->getValue();

        // Find the matching object in departmentConfigObject
        $matchingDepartment = array_filter($departmentConfigObject, function ($department) use ($departmentName) {
            return $department['DepartmentName'] === $departmentName;
        });

        if (empty($matchingDepartment)) {
            // If no match found, write "Department name not found" in the Department Number column
            $worksheet->setCellValue($departmentNumberColumnLetter . $row, "Department name not found");
        } else {
            // Get the first matched department object
            $department = reset($matchingDepartment);

            // Check if the DepartmentNumber exists
            $DepartmentNumber = $department['DepartmentNumber'];
            if (isset($DepartmentNumber)) {
                // Write the DepartmentNumber in the specified column
                $worksheet->setCellValue($departmentNumberColumnLetter . $row, $DepartmentNumber);
            } else {
                // If DepartmentNumber does not exist, write "Department number not exists"
                $worksheet->setCellValue($departmentNumberColumnLetter . $row, "Department number not exists");
            }
        }
    }

    // Return the modified Spreadsheet
    return $newProductsList;
}



?>


