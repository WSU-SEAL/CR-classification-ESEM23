package yunogum.MetricCalculator;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Dictionary;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Set;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.tree.Tree;

import yunogum.AstUtils;
import yunogum.PythonFileData;

public abstract class ElseMetrics extends MetricCalculator{

    //else can appear as modified/updated/move on it's own without accompanying parent being in the appropriate classifier.map
    //GUMtree will add both parent and child in the map If parent is modified/updated
    //we only want the else aka child suites  
    //to avoid overcounting we only check trees  that are suite and cild to if
    public int countElse(Iterable<Tree> iter, PythonFileData fileData, boolean isSrc){
        int count = 0;
        for (Tree t : iter) {

            
            if(AstUtils.isTreeType(t, AstUtils.SUITE)){
                Tree parent = t.getParent();
                if(AstUtils.isTreeType(parent, AstUtils.IF_STMT)){
                    if( 
                        (
                            (isSrc && !fileData.isSrcNodeInExtendedRange(t) && !fileData.checkIfInFunctionScope(t)) ||
                            (!isSrc && !fileData.isInsertedNodeInExtendedRange(t) 
                        )   
                    )){
                        continue;
                    }
                    count++;
                }
            }
        }

        return count;
    }


}