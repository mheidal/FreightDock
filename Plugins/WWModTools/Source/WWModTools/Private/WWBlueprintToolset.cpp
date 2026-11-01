#include "WWBlueprintToolset.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "EdGraphUtilities.h"
#include "Engine/Blueprint.h"
#include "FileHelpers.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_FunctionResult.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Logging/TokenizedMessage.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/StringOutputDevice.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	UBlueprint* LoadBlueprint(const FString& BlueprintPath, const TCHAR* Tool)
	{
		FString ObjectPath = BlueprintPath;
		if (!ObjectPath.Contains(TEXT(".")))
		{
			ObjectPath += TEXT(".") + FPaths::GetBaseFilename(BlueprintPath);
		}
		UBlueprint* Blueprint = LoadObject<UBlueprint>(nullptr, *ObjectPath);
		if (!Blueprint)
		{
			UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("%s: no Blueprint at '%s'."), Tool, *ObjectPath));
		}
		return Blueprint;
	}

	UEdGraph* FindGraph(UBlueprint* Blueprint, const FString& GraphName)
	{
		TArray<UEdGraph*> Graphs;
		Blueprint->GetAllGraphs(Graphs);
		for (UEdGraph* Graph : Graphs)
		{
			if (Graph && Graph->GetName() == GraphName)
			{
				return Graph;
			}
		}
		return nullptr;
	}

	bool ParsePinType(const FString& Text, FEdGraphPinType& OutType, FString& OutError)
	{
		OutType = FEdGraphPinType();
		FStringOutputDevice Errors;
		const TCHAR* End = FEdGraphPinType::StaticStruct()->ImportText(
			*Text, &OutType, nullptr, PPF_None, &Errors, TEXT("FEdGraphPinType"));
		if (!End || OutType.PinCategory.IsNone())
		{
			OutError = FString::Printf(TEXT("bad pin type '%s' %s"), *Text, *Errors);
			return false;
		}
		return true;
	}

	FString PinTypeText(const FEdGraphPinType& Type)
	{
		FString Out;
		FEdGraphPinType::StaticStruct()->ExportText(Out, &Type, nullptr, nullptr, PPF_None, nullptr);
		return Out;
	}

	TSharedPtr<FJsonValue> ReadJsonFile(const FString& File, const TCHAR* Tool)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *File))
		{
			UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("%s: cannot read '%s'."), Tool, *File));
			return nullptr;
		}
		TSharedPtr<FJsonValue> Root;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
		{
			UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("%s: '%s' is not valid JSON."), Tool, *File));
			return nullptr;
		}
		return Root;
	}

	struct FVarSpec
	{
		FName Name;
		FString Type;
		FString Default;
	};

	TArray<FVarSpec> ReadVars(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field)
	{
		TArray<FVarSpec> Vars;
		const TArray<TSharedPtr<FJsonValue>>* Items = nullptr;
		if (Object->TryGetArrayField(Field, Items))
		{
			for (const TSharedPtr<FJsonValue>& Item : *Items)
			{
				const TSharedPtr<FJsonObject> Var = Item->AsObject();
				if (Var.IsValid())
				{
					FVarSpec& Spec = Vars.AddDefaulted_GetRef();
					Spec.Name = FName(Var->GetStringField(TEXT("name")));
					Spec.Type = Var->GetStringField(TEXT("type"));
					Var->TryGetStringField(TEXT("default"), Spec.Default);
				}
			}
		}
		return Vars;
	}

	TArray<FString> ReadStrings(const TSharedPtr<FJsonValue>& Value)
	{
		TArray<FString> Out;
		if (Value.IsValid() && Value->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& Item : Value->AsArray())
			{
				Out.Add(Item->AsString());
			}
		}
		return Out;
	}

	UEdGraphNode* FindLabelled(const TSet<UEdGraphNode*>& Nodes, const FString& Label)
	{
		for (UEdGraphNode* Node : Nodes)
		{
			if (Node && Node->NodeComment == Label)
			{
				return Node;
			}
		}
		return nullptr;
	}

	void Connect(const UEdGraphSchema_K2* Schema, UEdGraphPin* A, UEdGraphPin* B, const FString& What, TArray<FString>& Report)
	{
		if (!A || !B)
		{
			Report.Add(FString::Printf(TEXT("  missing pin: %s"), *What));
		}
		else if (!Schema->TryCreateConnection(A, B))
		{
			Report.Add(FString::Printf(TEXT("  could not connect: %s"), *What));
		}
	}

	void ResetUserPins(UK2Node_EditablePinBase* Node)
	{
		TArray<FName> Names;
		for (const TSharedPtr<FUserPinInfo>& Pin : Node->UserDefinedPins)
		{
			Names.Add(Pin->PinName);
		}
		for (const FName& Name : Names)
		{
			Node->RemoveUserDefinedPinByName(Name);
		}
	}
}

FString UWWBlueprintToolset::ListGraphs(const FString& BlueprintPath)
{
	UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, TEXT("ListGraphs"));
	if (!Blueprint)
	{
		return FString();
	}
	TArray<FString> Lines;
	for (UEdGraph* Graph : Blueprint->UbergraphPages)
	{
		Lines.Add(FString::Printf(TEXT("event graph %s (%d nodes)"), *Graph->GetName(), Graph->Nodes.Num()));
	}
	for (UEdGraph* Graph : Blueprint->FunctionGraphs)
	{
		Lines.Add(FString::Printf(TEXT("function %s (%d nodes)"), *Graph->GetName(), Graph->Nodes.Num()));
	}
	for (UEdGraph* Graph : Blueprint->MacroGraphs)
	{
		Lines.Add(FString::Printf(TEXT("macro %s (%d nodes)"), *Graph->GetName(), Graph->Nodes.Num()));
	}
	for (const FBPVariableDescription& Var : Blueprint->NewVariables)
	{
		Lines.Add(FString::Printf(TEXT("variable %s %s = %s"), *Var.VarName.ToString(), *PinTypeText(Var.VarType), *Var.DefaultValue));
	}
	return FString::Join(Lines, TEXT("\n"));
}

FString UWWBlueprintToolset::EnsureVariables(const FString& BlueprintPath, const FString& VariablesFile)
{
	UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, TEXT("EnsureVariables"));
	const TSharedPtr<FJsonValue> Root = Blueprint ? ReadJsonFile(VariablesFile, TEXT("EnsureVariables")) : nullptr;
	if (!Root.IsValid())
	{
		return FString();
	}
	TSharedPtr<FJsonObject> Wrapper = MakeShared<FJsonObject>();
	Wrapper->SetField(TEXT("vars"), Root);

	TArray<FString> Report;
	for (const FVarSpec& Spec : ReadVars(Wrapper, TEXT("vars")))
	{
		FEdGraphPinType Type;
		FString Error;
		if (!ParsePinType(Spec.Type, Type, Error))
		{
			Report.Add(FString::Printf(TEXT("%s: %s"), *Spec.Name.ToString(), *Error));
			continue;
		}
		const int32 Index = FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, Spec.Name);
		if (Index == INDEX_NONE)
		{
			const bool bAdded = FBlueprintEditorUtils::AddMemberVariable(Blueprint, Spec.Name, Type, Spec.Default);
			Report.Add(FString::Printf(TEXT("%s: %s"), *Spec.Name.ToString(), bAdded ? TEXT("added") : TEXT("could not be added")));
			continue;
		}
		bool bChanged = false;
		if (!(Blueprint->NewVariables[Index].VarType == Type))
		{
			FBlueprintEditorUtils::ChangeMemberVariableType(Blueprint, Spec.Name, Type);
			bChanged = true;
		}
		FBPVariableDescription& Var = Blueprint->NewVariables[FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, Spec.Name)];
		if (Var.DefaultValue != Spec.Default)
		{
			Blueprint->Modify();
			Var.DefaultValue = Spec.Default;
			bChanged = true;
		}
		Report.Add(FString::Printf(TEXT("%s: %s"), *Spec.Name.ToString(), bChanged ? TEXT("updated") : TEXT("unchanged")));
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	return FString::Join(Report, TEXT("\n"));
}

FString UWWBlueprintToolset::ImportFunction(const FString& BlueprintPath, const FString& SpecFile, bool SignatureOnly)
{
	UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, TEXT("ImportFunction"));
	const TSharedPtr<FJsonValue> Root = Blueprint ? ReadJsonFile(SpecFile, TEXT("ImportFunction")) : nullptr;
	const TSharedPtr<FJsonObject> Spec = Root.IsValid() ? Root->AsObject() : nullptr;
	if (!Spec.IsValid())
	{
		return FString();
	}
	const FString FunctionName = Spec->GetStringField(TEXT("function"));
	TArray<FString> Report;

	// the function graph, with its entry and one result node
	UEdGraph* Graph = nullptr;
	for (UEdGraph* Existing : Blueprint->FunctionGraphs)
	{
		if (Existing && Existing->GetName() == FunctionName)
		{
			Graph = Existing;
		}
	}
	if (!Graph)
	{
		Graph = FBlueprintEditorUtils::CreateNewGraph(Blueprint, FName(FunctionName), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());
		FBlueprintEditorUtils::AddFunctionGraph<UClass>(Blueprint, Graph, true, nullptr);
		Report.Add(FString::Printf(TEXT("created %s"), *FunctionName));
	}
	TArray<UK2Node_FunctionEntry*> Entries;
	Graph->GetNodesOfClass(Entries);
	if (Entries.Num() == 0)
	{
		UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("ImportFunction: %s has no entry node."), *FunctionName));
		return FString();
	}
	UK2Node_FunctionEntry* Entry = Entries[0];
	TArray<UK2Node_FunctionResult*> Results;
	Graph->GetNodesOfClass(Results);
	UK2Node_FunctionResult* Result = Results.Num() > 0 ? Results[0] : nullptr;
	if (!Result)
	{
		FGraphNodeCreator<UK2Node_FunctionResult> Creator(*Graph);
		Result = Creator.CreateNode();
		Result->NodePosX = Entry->NodePosX + 1600;
		Result->NodePosY = Entry->NodePosY;
		Creator.Finalize();
	}

	// signature
	Entry->Modify();
	Result->Modify();
	ResetUserPins(Entry);
	ResetUserPins(Result);
	for (const FVarSpec& Pin : ReadVars(Spec, TEXT("inputs")))
	{
		FEdGraphPinType Type;
		FString Error;
		if (ParsePinType(Pin.Type, Type, Error))
		{
			Entry->CreateUserDefinedPin(Pin.Name, Type, EGPD_Output, false);
		}
		else
		{
			Report.Add(FString::Printf(TEXT("  input %s: %s"), *Pin.Name.ToString(), *Error));
		}
	}
	for (const FVarSpec& Pin : ReadVars(Spec, TEXT("outputs")))
	{
		FEdGraphPinType Type;
		FString Error;
		if (ParsePinType(Pin.Type, Type, Error))
		{
			Result->CreateUserDefinedPin(Pin.Name, Type, EGPD_Input, false);
		}
		else
		{
			Report.Add(FString::Printf(TEXT("  output %s: %s"), *Pin.Name.ToString(), *Error));
		}
	}
	Entry->LocalVariables.Empty();
	for (const FVarSpec& Local : ReadVars(Spec, TEXT("locals")))
	{
		FEdGraphPinType Type;
		FString Error;
		if (!ParsePinType(Local.Type, Type, Error))
		{
			Report.Add(FString::Printf(TEXT("  local %s: %s"), *Local.Name.ToString(), *Error));
		}
		else if (!FBlueprintEditorUtils::AddLocalVariable(Blueprint, Graph, Local.Name, Type, Local.Default))
		{
			Report.Add(FString::Printf(TEXT("  local %s could not be added"), *Local.Name.ToString()));
		}
	}
	bool bPure = false;
	Spec->TryGetBoolField(TEXT("pure"), bPure);
	if (bPure)
	{
		Entry->AddExtraFlags(FUNC_BlueprintPure);
	}
	else
	{
		Entry->ClearExtraFlags(FUNC_BlueprintPure);
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);

	FString T3DName;
	if (SignatureOnly || !Spec->TryGetStringField(TEXT("t3d"), T3DName) || T3DName.IsEmpty())
	{
		Report.Add(FString::Printf(TEXT("%s: signature set"), *FunctionName));
		return FString::Join(Report, TEXT("\n"));
	}

	// body: remove the old one, paste the new one
	FString T3D;
	const FString T3DFile = FPaths::Combine(FPaths::GetPath(SpecFile), T3DName);
	if (!FFileHelper::LoadFileToString(T3D, *T3DFile))
	{
		UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("ImportFunction: cannot read '%s'."), *T3DFile));
		return FString();
	}
	for (UEdGraphNode* Node : TArray<UEdGraphNode*>(Graph->Nodes))
	{
		if (Node && Node != Entry && Node != Result)
		{
			FBlueprintEditorUtils::RemoveNode(Blueprint, Node, true);
		}
	}
	Entry->BreakAllNodeLinks();
	Result->BreakAllNodeLinks();

	TSet<UEdGraphNode*> Pasted;
	FEdGraphUtilities::ImportNodesFromText(Graph, T3D, Pasted);
	Report.Add(FString::Printf(TEXT("%s: %d nodes pasted"), *FunctionName, Pasted.Num()));

	// wire the entry and return nodes to the pasted nodes, found by label
	const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
	auto LabelledPin = [&Pasted, &Report](const TArray<FString>& Ref) -> UEdGraphPin*
	{
		if (Ref.Num() < 2)
		{
			return nullptr;
		}
		UEdGraphNode* Node = FindLabelled(Pasted, Ref[0]);
		if (!Node)
		{
			Report.Add(FString::Printf(TEXT("  no node labelled %s"), *Ref[0]));
			return nullptr;
		}
		return Node->FindPin(FName(Ref[1]));
	};
	const TArray<FString> EntryRef = ReadStrings(Spec->TryGetField(TEXT("entry")));
	if (EntryRef.Num() >= 2)
	{
		Connect(Schema, Entry->FindPin(UEdGraphSchema_K2::PN_Then), LabelledPin(EntryRef),
			FString::Printf(TEXT("entry -> %s.%s"), *EntryRef[0], *EntryRef[1]), Report);
	}
	const TArray<TSharedPtr<FJsonValue>>* Returns = nullptr;
	if (Spec->TryGetArrayField(TEXT("returns"), Returns))
	{
		for (const TSharedPtr<FJsonValue>& Item : *Returns)
		{
			const TArray<FString> Ref = ReadStrings(Item);
			Connect(Schema, LabelledPin(Ref), Result->FindPin(UEdGraphSchema_K2::PN_Execute),
				FString::Printf(TEXT("%s -> return"), *FString::Join(Ref, TEXT("."))), Report);
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
	if (Spec->TryGetArrayField(TEXT("returnValues"), Values))
	{
		for (const TSharedPtr<FJsonValue>& Item : *Values)
		{
			const TArray<FString> Ref = ReadStrings(Item);
			if (Ref.Num() < 3)
			{
				Report.Add(TEXT("  returnValues entries need [node, pin, output]"));
				continue;
			}
			Connect(Schema, LabelledPin(Ref), Result->FindPin(FName(Ref[2])),
				FString::Printf(TEXT("%s.%s -> return %s"), *Ref[0], *Ref[1], *Ref[2]), Report);
		}
	}

	Graph->NotifyGraphChanged();
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	return FString::Join(Report, TEXT("\n"));
}

FString UWWBlueprintToolset::RemoveFunction(const FString& BlueprintPath, const FString& FunctionName)
{
	UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, TEXT("RemoveFunction"));
	if (!Blueprint)
	{
		return FString();
	}
	for (UEdGraph* Graph : Blueprint->FunctionGraphs)
	{
		if (Graph && Graph->GetName() == FunctionName)
		{
			FBlueprintEditorUtils::RemoveGraph(Blueprint, Graph, EGraphRemoveFlags::Recompile);
			return FString::Printf(TEXT("removed %s"), *FunctionName);
		}
	}
	UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("RemoveFunction: no function %s."), *FunctionName));
	return FString();
}

FString UWWBlueprintToolset::ExportGraph(const FString& BlueprintPath, const FString& GraphName, const FString& OutFile)
{
	UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, TEXT("ExportGraph"));
	UEdGraph* Graph = Blueprint ? FindGraph(Blueprint, GraphName) : nullptr;
	if (!Graph)
	{
		if (Blueprint)
		{
			UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("ExportGraph: no graph %s."), *GraphName));
		}
		return FString();
	}
	TSet<UObject*> Nodes;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node)
		{
			Nodes.Add(Node);
		}
	}
	FString T3D;
	FEdGraphUtilities::ExportNodesToText(Nodes, T3D);
	if (OutFile.IsEmpty())
	{
		return T3D;
	}
	if (!FFileHelper::SaveStringToFile(T3D, *OutFile))
	{
		UKismetSystemLibrary::RaiseScriptError(FString::Printf(TEXT("ExportGraph: cannot write '%s'."), *OutFile));
		return FString();
	}
	return FString::Printf(TEXT("%s: %d nodes written to %s"), *GraphName, Nodes.Num(), *OutFile);
}

FString UWWBlueprintToolset::CompileAndSave(const FString& BlueprintPath, bool Save)
{
	UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, TEXT("CompileAndSave"));
	if (!Blueprint)
	{
		return FString();
	}
	FCompilerResultsLog Results;
	Results.SetSourcePath(Blueprint->GetPathName());
	Results.SetSilentMode(true);
	FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::SkipSave, &Results);

	TArray<FString> Lines;
	Lines.Add(FString::Printf(TEXT("%d error(s), %d warning(s)"), Results.NumErrors, Results.NumWarnings));
	for (const TSharedRef<FTokenizedMessage>& Message : Results.Messages)
	{
		Lines.Add(FString::Printf(TEXT("[%s] %s"),
			*FTokenizedMessage::GetSeverityText(Message->GetSeverity()).ToString(), *Message->ToText().ToString()));
	}
	if (Save)
	{
		const bool bSaved = UEditorLoadingAndSavingUtils::SavePackages({ Blueprint->GetPackage() }, false);
		Lines.Add(bSaved ? TEXT("saved") : TEXT("save failed"));
	}
	return FString::Join(Lines, TEXT("\n"));
}
